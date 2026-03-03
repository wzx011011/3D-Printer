#ifndef ANALYTICS_DATA_UPLOAD_MANAGER_HPP
#define ANALYTICS_DATA_UPLOAD_MANAGER_HPP

#include <functional>
#include <mutex>
#include <condition_variable>
#include "nlohmann/json.hpp"

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
    ANALYTICS_GLOBAL_PRINT_PARAMS,
    ANALYTICS_OBJECT_PRINT_PARAMS,
    ANALYTICS_SLICE_PLATE,
    ANALYTICS_FIRST_LAUNCH,
    ANALYTICS_PREFERENCES_CHANGED,
    ANALYTICS_SOFTWARE_LAUNCH,
    ANALYTICS_SOFTWARE_CRASH,
    ANALYTICS_BAD_ALLOC,
    ANALYTICS_SOFTWARE_CLOSE,
    ANALYTICS_DEVICE_INFO,
    ANALYTICS_ACCOUNT_DEVICE_INFO,
    ANALYTICS_ONLINE_MODELS,
    ANALYTICS_PREPARE,
    ANALYTICS_PREVIEW,
    ANALYTICS_DEVICE,
    ANALYTICS_CLICK_HOME_PAGE_PROJECTS,
    ANALYTICS_CLICK_HOME_PAGE_ONLINE_PARAMS,
    ANALYTICS_CLICK_HOME_PAGE_TUTORIALS,
    ANALYTICS_CLICK_HOME_PAGE_PERSON_CENTER,
    ANALYTICS_CLICK_HOME_PAGE_FEEDBACK,
    ANALYTICS_CLICK_HOME_PAGE_MAKENOW,
    ANALYTICS_CLICK_HOME_PAGE_CREALITYMALL,
    ANALYTICS_MODEL_ACTION_ADD,
    ANALYTICS_MODEL_ACTION_ADD_PLATE,
    ANALYTICS_MODEL_ACTION_MOVE,
    ANALYTICS_MODEL_ACTION_ROTATE,
    ANALYTICS_MODEL_ACTION_AUTO_ORIENT,
    ANALYTICS_MODEL_ACTION_ARRANGE_ALL,
    ANALYTICS_MODEL_ACTION_LAY_ON_FACE,
    ANALYTICS_MODEL_ACTION_SPLIT_TO_OBJECTS,
    ANALYTICS_MODEL_ACTION_SPLIT_TO_PARTS,
    ANALYTICS_MODEL_ACTION_SCALE,
    ANALYTICS_MODEL_ACTION_HOLLOW,
    ANALYTICS_MODEL_ACTION_ADD_HOLE,
    ANALYTICS_MODEL_ACTION_CUT,
    ANALYTICS_MODEL_ACTION_BOOLEAN,
    ANALYTICS_MODEL_ACTION_MEASURE,
    ANALYTICS_MODEL_ACTION_SUPPORT_PAINT,
    ANALYTICS_MODEL_ACTION_ZSEAM_PAINT,
    ANALYTICS_MODEL_ACTION_VARIABLE_LAYER,
    ANALYTICS_MODEL_ACTION_PAINT,
    ANALYTICS_MODEL_ACTION_EMBOSS,
    ANALYTICS_MODEL_ACTION_ASSEMBLY_VIEW,
    ANALYTICS_AI_SERVICE_CALL,
    ANALYTICS_GOTO_WIKI,
    ANALYTICS_GOTO_SUPPORT,
    ANALYTICS_TAB_HOME
};

struct AnalyticsEventPayload {
    AnalyticsDataEventType type;
    nlohmann::json data;
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
    void triggerUploadTasksWithPayload(AnalyticsUploadTiming triggerTiming, const AnalyticsEventPayload& payload, int plate_idx, const std::string& device_mac);

    void mark_analytics_project_info(const std::string& full_url,
                                               const std::string& model_id,
                                               const std::string& file_id,
                                               const std::string& file_format,
                                               const std::string& name);

    void set_analytics_project_info_valid(bool valid);
    void clear_analytics_project_info();

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
    void uploadOnlineModelsEvent();
    void uploadPrepareEvent();
    void uploadPreviewEvent();
    void uploadDeviceEvent();
    void uploadClickHomePageProjectsEvent();
    void uploadClickHomePageOnlineParamsEvent();
    void uploadClickHomePageTutorialsEvent();
    void uploadClickHomePagePersonCenterEvent();
    void uploadClickHomePageFeedbackEvent();
    void uploadClickHomePageMakenowEvent();
    void uploadClickHomePageCrealitymallEvent();
    void uploadModelActionAddEvent();
    void uploadModelActionAddPlateEvent();
    void uploadModelActionMoveEvent();
    void uploadModelActionRotateEvent();
    void uploadModelActionAutoOrientEvent();
    void uploadModelActionArrangeAllEvent();
    void uploadModelActionLayOnFaceEvent();
    void uploadModelActionSplitToObjectsEvent();
    void uploadModelActionSplitToPartsEvent();
    void uploadModelActionScaleEvent();
    void uploadModelActionHollowEvent();
    void uploadModelActionAddHoleEvent();
    void uploadModelActionCutEvent();
    void uploadModelActionBooleanEvent();
    void uploadModelActionMeasureEvent();
    void uploadModelActionSupportPaintEvent();
    void uploadModelActionZseamPaintEvent();
    void uploadModelActionVariableLayerEvent();
    void uploadModelActionPaintEvent();
    void uploadModelActionEmbossEvent();
    void uploadModelActionAssemblyViewEvent();
    void uploadAiServiceCallEvent();

    void track_model_action(const std::string& event_name, nlohmann::json& js);

private:
    AnalyticsProjectInfo m_analytics_project_info;

};

} // namespace GUI
} // namespace Slic3r

#endif // ANALYTICS_DATA_UPLOAD_MANAGER_HPP
