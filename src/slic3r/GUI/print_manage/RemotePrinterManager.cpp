#include "RemotePrinterManager.hpp"
#include <future>
#include <string>

namespace RemotePrint {

size_t read_callback(void* ptr, size_t size, size_t nmemb, void* stream)
{
    std::ifstream* file = static_cast<std::ifstream*>(stream);
    file->read(static_cast<char*>(ptr), size * nmemb);
    return file->gcount();
}

int progress_callback(void* ptr, curl_off_t totalToDownload, curl_off_t nowDownloaded, curl_off_t totalToUpload, curl_off_t nowUploaded)
{
    auto* progressCallback = static_cast<std::function<void(float)>*>(ptr);
    if (totalToUpload > 0 && progressCallback) {
        (*progressCallback)(static_cast<float>(nowUploaded) / totalToUpload * 100.0f);
    }
    return 0;
}

RemotePrinterManager::RemotePrinterManager():stop_flag(false) 
{
//     m_pLanPrinterInterface = new LanPrinterInterface();
//     m_pOctoPrinterInterface = new OctoPrintInterface();
    m_pKlipperInterface = new KlipperInterface();
    m_pKlipper4408Interface = new Klipper4408Interface();
    m_pKlipperCXInterface = new KlipperCXInterface();

    auto	t = std::thread(&RemotePrinterManager::uploadThread, this);
	t.detach();
    for (int i = 0; i < 3; ++i) {
            m_multUploadThreads.emplace_back([this] { workerThread(); });
        }
}
void RemotePrinterManager::workerThread()
{
    while (true) {
            std::function<void()> task;
            
            {
                std::unique_lock<std::mutex> lock(queue_mutex);
                condition.wait(lock, [this] {
                    return stop_flag || !tasks.empty();
                });
                
                if (stop_flag && tasks.empty()) {
                    return;
                }
                
                task = std::move(tasks.front());
                tasks.pop();
            }
            
            task(); // 执行下载任务
        }
}
RemotePrinterManager::~RemotePrinterManager()
{
    m_bExit = true;
    stop_flag = true;
    m_cvUpload.notify_all();
    condition.notify_all();
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    for (int i = 0; i < 3; ++i) {
            if (m_multUploadThreads[i].joinable()) {
                m_multUploadThreads[i].join();
            }
     }
//     delete m_pLanPrinterInterface;
//     delete m_pOctoPrinterInterface;
    delete m_pKlipperInterface;
    delete m_pKlipper4408Interface;
    delete m_pKlipperCXInterface;
}

void RemotePrinterManager::uploadThread() 
{
    while (!m_bExit) {
        std::unique_lock<std::mutex> lock(m_mtxUpload);
        m_cvUpload.wait(lock, [this] { return !m_uploadTasks.empty() || m_bExit; });

        if (m_bExit) break;

        auto task = std::move(m_uploadTasks.front());
        m_uploadTasks.pop_front();
        lock.unlock();

        auto ipAddress = std::get<0>(task);
        auto filename = std::get<1>(task);
        auto filePath = std::get<2>(task);
        auto progress_call_back = std::get<3>(task);
        auto error_call_back = std::get<4>(task);
        auto onCompleteCall = std::get<5>(task);

        pushFile(ipAddress, filename, filePath, progress_call_back, error_call_back, onCompleteCall);
    }
}

void RemotePrinterManager::pushUploadTasks(const std::string& ipAddress, const std::string& fileName, const std::string& filePath, std::function<void(std::string, float,double)> progressCallback, std::function<void(std::string, int)> uploadStatusCallback, std::function<void(std::string, std::string)> onCompleteCallback) 
{
    std::lock_guard<std::mutex> lock(m_mtxUpload);
    m_uploadTasks.emplace_back(ipAddress, fileName, filePath, progressCallback, uploadStatusCallback, onCompleteCallback);
    m_cvUpload.notify_one();
}
void RemotePrinterManager::addDownloadTask(const std::function<void()>& task) {
        {
            std::unique_lock<std::mutex> lock(queue_mutex);
            tasks.push(task);
        }
        condition.notify_one();
    }
void RemotePrinterManager::pushUploadMultTasks(const std::string& ipAddress, const std::string& fileName, const std::string& filePath, std::function<void(std::string, float,double)> progressCallback, std::function<void(std::string, int)> uploadStatusCallback, std::function<void(std::string, std::string)> onCompleteCallback) 
{
    addDownloadTask([=]() {
        pushFile(ipAddress, fileName, filePath, progressCallback, uploadStatusCallback, onCompleteCallback);
    });
    //m_uploadTasks.emplace_back(ipAddress, fileName, filePath, progressCallback, uploadStatusCallback, onCompleteCallback);

}
void RemotePrinterManager::uploadFileByLan(const std::string& ipAddress, const std::string& fileName, const std::string& filePath, std::function<void(float,double)> progressCallback, std::function<void(std::string, int)> uploadStatusCallback, std::function<void(std::string, std::string)> onCompleteCallback) 
{
    m_pLanPrinterInterface->sendFileToDevice(ipAddress,fileName,filePath,progressCallback,nullptr,nullptr);
}

void RemotePrinterManager::cancelUpload(const std::string& ipAddress) { 
    //从查询队列中是否有未执行的任务，如果有则移除
    std::lock_guard<std::mutex> lock(m_mtxUpload);
    for (auto it = m_uploadTasks.begin(); it != m_uploadTasks.end(); ) {
        if (std::get<0>(*it) == ipAddress) {
            auto error_call_back = std::get<4>(*it) ;
            error_call_back(ipAddress,601);
            m_uploadTasks.erase(it); // 使用erase方法直接删除任务
            return;
        } else {
            ++it;
        }
    }

    m_cancelUploadMap[ipAddress] = true;

    RemotePrinerType printerType = determinePrinterType(ipAddress); 
    switch (printerType) {
    case RemotePrinerType::REMOTE_PRINTER_TYPE_KLIPPER4408:
        m_pKlipper4408Interface->cancelSendFileToDevice(ipAddress);
        break;
    case RemotePrinerType::REMOTE_PRINTER_TYPE_KLIPPER:
        m_pKlipperInterface->cancelSendFileToDevice();
        break;
    case RemotePrinerType::REMOTE_PRINTER_TYPE_CX:
        m_pKlipperCXInterface->cancelSendFileToDevice();
        break;
    default: break;
    }
}

void RemotePrinterManager::setOldPrinterMap(std::string& ipAddress)
{
    oldPrinters.push_back(ipAddress);
}

void RemotePrinterManager::setKlipperPrinterMap(const std::string& ipAddress,int port)
{
    mapKlipperPort[ipAddress] = port;
}

int RemotePrinterManager::getKlipperPrinterMap(const std::string& ipAddress)
{
    for (const auto& pair : mapKlipperPort)
    {
        if (pair.first == ipAddress)
        {
            return pair.second;
        }
    }
    return 80;
}

void RemotePrinterManager::pushFile(const std::string& ipAddress, const std::string& fileName, const std::string& filePath, 
    std::function<void(std::string, float,double)> progressCallback, 
    std::function<void(std::string, int)> uploadStatusCallback,
    std::function<void(std::string, std::string)> onCompleteCallback)
{
    m_lastUploadMap[ipAddress]   = {fileName, filePath, progressCallback, uploadStatusCallback, onCompleteCallback};
    RemotePrinerType printerType = determinePrinterType(ipAddress);

    bool uploadCompleted  = false;
    auto lastProgressTime = std::chrono::steady_clock::now();
    auto sendFile = [&](auto* printerInterface, auto&&... args) {
        std::future<void> future = printerInterface->sendFileToDevice(std::forward<decltype(args)>(args)...,
            [=, &lastProgressTime](float progress, double speed) {
                lastProgressTime = std::chrono::steady_clock::now();
                if (progressCallback) {
                    progressCallback(ipAddress, progress,speed);
                }
            },
            [=](int statusCode) {
                if (uploadStatusCallback) {
                    uploadStatusCallback(ipAddress, statusCode);
                }
            },
            [=, &uploadCompleted](std::string body) {
                uploadCompleted = true;
                m_retryCountMap.erase(ipAddress);
                if(onCompleteCallback)onCompleteCallback(ipAddress, body);
            }
        );
#if 0    
        int& retryCount = m_retryCountMap[ipAddress];
        while (retryCount <= MAX_RETRY) {
            auto status = future.wait_for(std::chrono::milliseconds(100));
            if (uploadCompleted) {
                break;
            }

            auto now          = std::chrono::steady_clock::now();
            auto heartbeatGap = std::chrono::duration_cast<std::chrono::seconds>(now - lastProgressTime).count();
            if (status != std::future_status::ready || heartbeatGap <= m_uploadTimeoutSeconds) {
                continue;
            }

            retryCount++;
            if (retryCount > MAX_RETRY) {
                BOOST_LOG_TRIVIAL(error) << "Upload failed for " << ipAddress << " after " << MAX_RETRY << " retries.";
                if (uploadStatusCallback) {
                    m_retryCountMap.erase(ipAddress);
                    uploadStatusCallback(ipAddress, 3);
                }
                break;
            }

            if (m_cancelUploadMap[ipAddress]) {
                BOOST_LOG_TRIVIAL(info) << "Upload canceled for " << ipAddress;
                m_retryCountMap.erase(ipAddress);
                m_cancelUploadMap.erase(ipAddress);
                break;
            }

            BOOST_LOG_TRIVIAL(warning) << "Upload retry for " << ipAddress << " (" << retryCount << "/" << MAX_RETRY << ")";
            retryUpload(ipAddress);
            lastProgressTime = std::chrono::steady_clock::now();
            break;
        }
#else
        while (true) {
            auto status = future.wait_for(std::chrono::milliseconds(100));
            if (status == std::future_status::ready)
                break;
        }
#endif

    };

   switch (printerType)
    {
        case RemotePrinerType::REMOTE_PRINTER_TYPE_LAN:
            sendFile(m_pLanPrinterInterface, ipAddress, fileName, filePath);
            break;
        case RemotePrinerType::REMOTE_PRINTER_TYPE_OCTOPRINT:
            m_pOctoPrinterInterface->sendFileToDevice(ipAddress, "", filePath);
            break;
        case RemotePrinerType::REMOTE_PRINTER_TYPE_KLIPPER:
            sendFile(m_pKlipperInterface, ipAddress, getKlipperPrinterMap(ipAddress), fileName, filePath);
            break;
        case RemotePrinerType::REMOTE_PRINTER_TYPE_KLIPPER4408:
            sendFile(m_pKlipper4408Interface, ipAddress, 80, fileName, filePath);
            break;
        case RemotePrinerType::REMOTE_PRINTER_TYPE_CX:
            sendFile(m_pKlipperCXInterface, ipAddress, 80, fileName, filePath);
            break;
        default:
            break;
    }
}

RemotePrinerType RemotePrinterManager::determinePrinterType(const std::string& ipAddress)
{
    bool isExists = (std::find(oldPrinters.begin(),oldPrinters.end(), ipAddress) != oldPrinters.end());
    if(isExists)
        return RemotePrinerType::REMOTE_PRINTER_TYPE_LAN;

    for (const auto& pair : mapKlipperPort)
    {
        if (pair.first == ipAddress)
        {
            return RemotePrinerType::REMOTE_PRINTER_TYPE_KLIPPER;
        }
    }

    if(ipAddress.find('.') !=-1)
        return RemotePrinerType::REMOTE_PRINTER_TYPE_KLIPPER4408;

    return RemotePrinerType::REMOTE_PRINTER_TYPE_CX;
}
void RemotePrinterManager::retryUpload(const std::string& ipAddress)
{

    auto it = m_lastUploadMap.find(ipAddress);
    if (it != m_lastUploadMap.end()) {
        const UploadTask& task = it->second;

        pushUploadTasks(ipAddress, task.fileName, task.filePath, task.progressCallback, task.uploadStatusCallback, task.onCompleteCallback);

        m_cvUpload.notify_one();
    } else {
        std::cerr << "[RetryUpload] No previous upload task found for IP: " << ipAddress << std::endl;
    }
}

}
