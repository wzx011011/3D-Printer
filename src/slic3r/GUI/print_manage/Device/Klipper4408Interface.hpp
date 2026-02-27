#ifndef KLIPPER4408_INTERFACE_H
#define KLIPPER4408_INTERFACE_H

#include <future>
#include <functional>
#include <string>
#include "slic3r/Utils/Http.hpp"
#include "slic3r/GUI/FileUploader.hpp"
namespace RemotePrint {
	class Klipper4408Interface {
public:
	Klipper4408Interface();
	virtual ~Klipper4408Interface();

	std::future<void> sendFileToDevice(const std::string& serverIp, int port, const std::string& uploadFileName, const std::string& localFilePath, std::function<void(float,double)> progressCallback, std::function<void(int)> uploadStatusCallback, std::function<void(std::string)> onCompleteCallback);

	void cancelSendFileToDevice(std::string ipAddress = "");

private:
	const std::string urlSuffixUpload = "/upload/";
    std::map<std::string, Slic3r::Http*> mapHttp; // ipAddress -> port
	std::map<std::string, HttpFileUploader*> mapFileUploader; // ipAddress -> port
	//Slic3r::Http*     m_pHttp         = nullptr;
    bool              m_bCancelSend   = false;
    };
}


#endif // KLIPPER4408_INTERFACE_H
