#ifndef ANALYTICS_DATA_UPLOAD_MANAGER_HPP
#define ANALYTICS_DATA_UPLOAD_MANAGER_HPP

#include <functional>
#include <mutex>
#include <condition_variable>

namespace Slic3r {
namespace GUI {

// when to upload analytics data
enum class AnalyticsUploadTiming {
    ON_CLICK_START_PRINT_CMD,        // when user clicks the ("start print" or "send only") command(on SendToPrinter front page)
    ON_SLICE_PLATE_CMD,    //when user clicks the (slice or slice all) command
    ON_FIRST_LAUNCH,      // when software is launched for the first time (when "AppData\Roaming\Creality" directory first created)
    ON_PREFERENCES_CHANGED,    //when user close the preference dialog
    ON_SOFTWARE_LAUNCH,      //when creality slicer launch, it could possibly launch multiple times every day
    ON_SOFTWARE_CRASH,        // when software crash and then reboot
    ON_SOFTWARE_CLOSE        // when software close
};

// what kind of data to upload
enum class AnalyticsDataEventType {
    ANALYTICS_GLOBAL_PRINT_PARAMS, // global print params
    ANALYTICS_OBJECT_PRINT_PARAMS, // object print params
    ANALYTICS_SLICE_PLATE,    // slice plate
    ANALYTICS_FIRST_LAUNCH,   // software first launch (when "AppData\Roaming\Creality" directory first created)
    ANALYTICS_PREFERENCES_CHANGED,    //user preferences changed
    ANALYTICS_SOFTWARE_LAUNCH,     //creality slicer launch
    ANALYTICS_SOFTWARE_CRASH,       // software crash
    ANALYTICS_BAD_ALLOC,           // software crash
    ANALYTICS_SOFTWARE_CLOSE,      // software close
    ANALYTICS_DEVICE_INFO,         // print device info (un_login), local net(from deviceInfo.json)
    ANALYTICS_ACCOUNT_DEVICE_INFO  // account device info(user login), from account_device_info.json
};

struct AnalyticsProjectInfo {
    std::string url;
    std::string file_id;
    std::string file_format;
    std::string model_id;
    std::string name;

    bool is_valid = false;
};

class AnalyticsDataUploadManager
{
public:
    static AnalyticsDataUploadManager& getInstance()
    {
        static std::unique_ptr<AnalyticsDataUploadManager> instance;
        static std::once_flag flag;
        std::call_once(flag, []() {
            instance.reset(new AnalyticsDataUploadManager());
        });
        return *instance;
    }

    ~AnalyticsDataUploadManager();

    void triggerUploadTasks(AnalyticsUploadTiming triggerTiming, const std::vector<AnalyticsDataEventType>& dataEventTypes, int plate_idx = 0, const std::string& device_mac = "");

    void mark_analytics_project_info(const std::string& full_url,
                                               const std::string& model_id,
                                               const std::string& file_id,
                                               const std::string& file_format,
                                               const std::string& name);

    void set_analytics_project_info_valid(bool valid);
    void clear_analytics_project_info();

    // slice822 click event logging
    // Parameters:
    //  - module: module name (function_module)
    //  - id: module id (module_id)
    // Builds payload: { slice822: { event_type, function_module, module_id, app_version, operating_system, timestamp } }
    static void uploadSlice822ClickEvent(const std::string& module, int id=1);

private:
    AnalyticsDataUploadManager();

    AnalyticsDataUploadManager(const AnalyticsDataUploadManager&)            = delete;
    AnalyticsDataUploadManager& operator=(const AnalyticsDataUploadManager&) = delete;

    void processUploadData(AnalyticsDataEventType dataEventType, int plate_idx, const std::string& device_mac);

    void uploadGlobalPrintParams(int plate_idx, const std::string& device_mac);
    void uploadObjectPrintParams(int plate_idx,const std::string& device_mac);
    void uploadSlicePlateEventData();
    void uploadFirstLaunchEventData();
    void uploadPreferencesChangedData();
    void uploadSoftwareLaunchData();
    void uploadSoftwareCrashData();
    void uploadSoftwareBadAlloc();
    void uploadSoftwareCloseData();
    void uploadDeviceInfoData();
    void uploadAccountDeviceInfoData();

private:
    AnalyticsProjectInfo m_analytics_project_info;

};

} // namespace GUI
} // namespace Slic3r

#endif // ANALYTICS_DATA_UPLOAD_MANAGER_HPP