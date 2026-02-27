#ifndef slic3r_GUI_CurlConnectionPool_hpp_
#define slic3r_GUI_CurlConnectionPool_hpp_
#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <curl/curl.h>

class CurlConnectionPool {
public:
    // 构造函数，指定最大并发连接数
    explicit CurlConnectionPool(int max_connections = 5);
    
    // 析构函数
    ~CurlConnectionPool();
    
    // 添加下载任务
    bool addDownload(const std::string url, const std::string filename);
    
    // 执行所有下载任务
    void performDownloads();
    
    // 禁止拷贝和赋值
    CurlConnectionPool(const CurlConnectionPool&) = delete;
    CurlConnectionPool& operator=(const CurlConnectionPool&) = delete;

private:
    // 下载项结构
    struct DownloadItem {
        std::string url;
        std::string filename;
        boost::nowide::ofstream stream;
        
        DownloadItem(const std::string& u, const std::string& f) 
            : url(u), filename(f), stream(f,boost::nowide::ofstream::binary) {}
        
        // 移动构造函数
        DownloadItem(DownloadItem&& other) noexcept
            : url(std::move(other.url)),
              filename(std::move(other.filename)){}
        
        // 禁止拷贝
        DownloadItem(const DownloadItem&) = delete;
        DownloadItem& operator=(const DownloadItem&) = delete;
    };
    
    // 静态回调函数
    static size_t writeDataCallback(void* ptr, size_t size, size_t nmemb, void* userdata);
    
    // 清理完成的下载项
    void cleanupCompletedDownloads();
    
    // libcurl multi handle
    CURLM* multi_handle_;
    
    // 当前运行的下载数
    int still_running_;
    
    // 最大并发连接数
    int max_connections_;
    
    // 所有下载项
    std::vector<std::shared_ptr<DownloadItem>> download_items_;
    
    // 所有easy handles
    std::vector<CURL*> easy_handles_;
};
#endif