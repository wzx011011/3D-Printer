#include "AnalyticsDataUploadManager.hpp"
#include <future>
#include <string>

#include "slic3r/GUI/GUI_App.hpp"
#include "slic3r/GUI/Plater.hpp"
#include "slic3r/GUI/PartPlate.hpp"
#include "slic3r/GUI/MainFrame.hpp"
#include "nlohmann/json.hpp"
#include "libslic3r/Time.hpp"
#include "slic3r/GUI/print_manage/data/DataType.hpp"
#include "slic3r/GUI/print_manage/data/DataCenter.hpp"
#include "slic3r/GUI/print_manage/AccountDeviceMgr.hpp"
#include "CrProject.hpp"
#include "libslic3r/Platform.hpp"

namespace Slic3r {
namespace GUI {

// 获取系统架构信息的辅助函数
std::string get_system_architecture() {
    PlatformFlavor flavor = platform_flavor();
    switch (flavor) {
        case PlatformFlavor::OSXOnX86:
            return "x86_64";
        case PlatformFlavor::OSXOnArm:
            return "arm64";
        default:
            // 对于其他平台，使用编译时检测
#if defined(__x86_64__) || defined(_M_X64) || defined(__amd64)
            return "x86_64";
#elif defined(__aarch64__) || defined(_M_ARM64)
            return "arm64";
#elif defined(__i386__) || defined(_M_IX86)
            return "x86";
#elif defined(__arm__)
            return "arm";
#else
            return "unknown";
#endif
    }
}

template <typename T>
std::string serialize_with_semicolon(const std::vector<T>& items)
{
    std::ostringstream oss;
    for (size_t i = 0; i < items.size(); ++i) {
        if (i > 0) oss << ";";
        oss << items[i];
    }
    return oss.str();
}


AnalyticsDataUploadManager::AnalyticsDataUploadManager()
{
}

AnalyticsDataUploadManager::~AnalyticsDataUploadManager()
{
}

void AnalyticsDataUploadManager::triggerUploadTasks(AnalyticsUploadTiming triggerTiming, const std::vector<AnalyticsDataEventType>& dataEventTypes, int plate_idx, const std::string& device_mac)
{
    try
    {
        if(wxGetApp().is_privacy_checked()) {
            for (const auto& dataEventType : dataEventTypes) {
                processUploadData(dataEventType, plate_idx, device_mac);
            }
        }
    }
    catch (...)
    {

    }
}

void AnalyticsDataUploadManager::mark_analytics_project_info(const std::string& full_url,
                                            const std::string& model_id,
                                            const std::string& file_id,
                                            const std::string& file_format,
                                            const std::string& name)
{
    m_analytics_project_info.url = full_url;
    m_analytics_project_info.model_id = model_id;
    m_analytics_project_info.file_id = file_id;
    m_analytics_project_info.file_format = file_format;
    m_analytics_project_info.name = name;
}

void AnalyticsDataUploadManager::set_analytics_project_info_valid(bool valid)
{
    m_analytics_project_info.is_valid = valid;
}

void AnalyticsDataUploadManager::clear_analytics_project_info()
{
    m_analytics_project_info.url = "";
    m_analytics_project_info.model_id = "";
    m_analytics_project_info.file_id = "";
    m_analytics_project_info.file_format = "";
    m_analytics_project_info.name = "";

    m_analytics_project_info.is_valid = false;
}

void AnalyticsDataUploadManager::processUploadData(AnalyticsDataEventType dataEventType, int plate_idx, const std::string& device_mac)
{
#if AUTO_CONVERT_3MF
    return;
#endif
    switch (dataEventType)
    {
    case AnalyticsDataEventType::ANALYTICS_GLOBAL_PRINT_PARAMS: 
        uploadGlobalPrintParams(plate_idx, device_mac);
        break;

    case AnalyticsDataEventType::ANALYTICS_OBJECT_PRINT_PARAMS: 
        uploadObjectPrintParams(plate_idx,device_mac);
        break;

    case AnalyticsDataEventType::ANALYTICS_SLICE_PLATE:
        uploadSlicePlateEventData();
        break;

    case AnalyticsDataEventType::ANALYTICS_FIRST_LAUNCH: 
        uploadFirstLaunchEventData();
        break;

    case AnalyticsDataEventType::ANALYTICS_PREFERENCES_CHANGED:
        uploadPreferencesChangedData();
        break;

    case AnalyticsDataEventType::ANALYTICS_SOFTWARE_LAUNCH: 
        uploadSoftwareLaunchData();
        break;

    case AnalyticsDataEventType::ANALYTICS_SOFTWARE_CRASH:
        uploadSoftwareCrashData();
        break;

    case AnalyticsDataEventType::ANALYTICS_BAD_ALLOC: 
        uploadSoftwareBadAlloc(); 
        break;

    case AnalyticsDataEventType::ANALYTICS_SOFTWARE_CLOSE: 
        uploadSoftwareCloseData(); 
        break;

    case AnalyticsDataEventType::ANALYTICS_DEVICE_INFO:
        uploadDeviceInfoData();
        break;

    case AnalyticsDataEventType::ANALYTICS_ACCOUNT_DEVICE_INFO:
        uploadAccountDeviceInfoData();
        break;

    default:
        break;
    }
}

void AnalyticsDataUploadManager::uploadGlobalPrintParams(int plate_idx, const std::string& device_mac)
{
    Plater* plater = wxGetApp().plater();
    PartPlateList& plate_list = plater->get_partplate_list();
    PartPlate* plate = plate_list.get_plate(plate_idx);
    if(!plate)
        return;

    ModelObjectPtrs objs_on_plate = plate->get_objects_on_this_plate();
    if(objs_on_plate.size() <= 0)
        return;

    const Print& plate_print = plate->get_print();

    const DynamicPrintConfig& print_full_config = plate_print.full_print_config();

    Slic3r::AuxiliariesInfo auxiliaries_info = plater->get_auxiliaries_info();

    try
    {
        json js;

        js["printer_mac"]   = device_mac;
        //js["printer_mac"] = "FCEE2806B0DB"; // 测试时用的数据

        // according to document description
        js["type_code"] = "slice801";

        js["printer_model"] = print_full_config.opt_serialize("printer_model");
        js["print_uuid"] = plate_print.get_print_uuid();

        js["nozzle_type"] = print_full_config.opt_serialize("nozzle_type");

        js["curr_bed_type"] = print_full_config.opt_serialize("curr_bed_type");
        js["filament_colour"] = print_full_config.opt_serialize("filament_colour");

        float koef = wxGetApp().app_config->get("use_inches") == "1" ? GizmoObjectManipulation::in_to_mm : 1000.0;
        std::ostringstream ss1;
        ss1 << std::fixed << std::setprecision(2) << plate_print.print_statistics().total_used_filament / koef;
        js["total_material_length"] = ss1.str();
        
        std::ostringstream ss;
        ss << std::fixed << std::setprecision(2) << plate_print.print_statistics().total_weight;
        js["total_filament_cost"] = ss.str();

        wxString print_time = wxString::Format("%s", short_time(get_time_dhms(plate->get_slice_result()->print_statistics.modes[0].time))); 
        js["print_estimated_duration"] = print_time.ToStdString();

        //js["slice_preview_duration"] = "";

        js["slice_layer_count"] = wxString::Format("%d",plate_print.print_statistics().total_layer_count).ToStdString();

        std::vector<int> obj_loaded_ids;

        for (ModelObject* mo : objs_on_plate) {
            obj_loaded_ids.push_back(mo->from_loaded_id);
        }

        js["object_ids"] = serialize_with_semicolon(obj_loaded_ids);

        js["layer_height"] = print_full_config.opt_serialize("layer_height");
        js["initial_layer_print_height"]   = print_full_config.opt_serialize("initial_layer_print_height");
        js["curr_bed_type"] = print_full_config.opt_serialize("curr_bed_type");
        js["wall_loops"] = print_full_config.opt_serialize("wall_loops");

        js["sparse_infill_density"] = print_full_config.opt_serialize("sparse_infill_density");
        js["sparse_infill_pattern"] = print_full_config.opt_serialize("sparse_infill_pattern");
        js["enable_support"] = print_full_config.opt_serialize("enable_support");
        js["support_type"]          = print_full_config.opt_serialize("support_type");
        js["support_style"] = print_full_config.opt_serialize("support_style");
        js["support_threshold_angle"] = print_full_config.opt_serialize("support_threshold_angle");
        js["fan_min_speed"] = print_full_config.opt_serialize("fan_min_speed");
        js["fan_cooling_layer_time"]  = print_full_config.opt_serialize("fan_cooling_layer_time");
        js["fan_max_speed"]           = print_full_config.opt_serialize("fan_max_speed");
        js["slow_down_layer_time"]    = print_full_config.opt_serialize("slow_down_layer_time");
        js["close_fan_the_first_x_layers"] = print_full_config.opt_serialize("close_fan_the_first_x_layers");
        js["full_fan_speed_layer"]         = print_full_config.opt_serialize("full_fan_speed_layer");
        js["filament_type"] = print_full_config.opt_serialize("filament_type");
        js["filament_diameter"]            = print_full_config.opt_serialize("filament_diameter");
        js["default_filament_colour"]            = print_full_config.opt_serialize("default_filament_colour");
        js["default_filament_profile"]            = print_full_config.opt_serialize("default_filament_profile");
        js["default_filament_type"]            = print_full_config.opt_serialize("default_filament_type");

        //js["file_format"] = "";
        //js["source_path"] = "";
        //js["user_id"] = "";
        //js["collect_id"] = "";

        if(m_analytics_project_info.is_valid) {
            js["cloud_url"] = m_analytics_project_info.url;
            js["cloud_file_id"] = m_analytics_project_info.file_id;
            js["cloud_file_format"] = m_analytics_project_info.file_format;
            js["cloud_model_id"] = m_analytics_project_info.model_id;
            js["cloud_name"] = m_analytics_project_info.name;
        }

        js["application"] = auxiliaries_info.get_metadata_application();
        js["platform"] = auxiliaries_info.get_metadata_platform();
        js["projectInfoId"] = auxiliaries_info.get_metadata_project_id();

        js["operation_date"] = Slic3r::Utils::utc_timestamp(Slic3r::Utils::get_current_time_utc());
        js["app_version"] = GUI_App::format_display_version().c_str();
        js["operating_system"]      = wxGetOsDescription().ToStdString().c_str();

        wxGetApp().track_event("print_global_parameters", js.dump());
    }
    catch (const std::exception& err)
    {
        BOOST_LOG_TRIVIAL(error) << __FUNCTION__<< ": json create " << " got a generic exception, reason = " << err.what();
    } 
    catch (...) {
        BOOST_LOG_TRIVIAL(error) << __FUNCTION__ << ": json create " << " got an unknown exception";
    }

}

void AnalyticsDataUploadManager::uploadObjectPrintParams(int plate_idx,const std::string& device_mac)
{
    Plater* plater = wxGetApp().plater();
    PartPlateList& plate_list = plater->get_partplate_list();
    PartPlate* plate = plate_list.get_plate(plate_idx);
    if(!plate)
        return;

    ModelObjectPtrs objs_on_plate = plate->get_objects_on_this_plate();
    if(objs_on_plate.size() <= 0)
        return;

    const Print& plate_print = plate->get_print();

    const DynamicPrintConfig& print_full_config = plate_print.full_print_config();

    try
    {
        json js;

        js["printer_mac"]   = device_mac;
        //js["printer_mac"] = "FCEE2806B0DB";  // 测试时用的数据

        // according to document description
        js["type_code"] = "slice802";

        js["printer_model"] = print_full_config.opt_serialize("printer_model");
        js["print_uuid"] = plate_print.get_print_uuid();

        std::vector<int> obj_loaded_ids;

        std::vector<std::map<std::string, std::string>> obj_options;
        std::set<std::string> all_keys;

        for (ModelObject* mo : objs_on_plate) {
            obj_loaded_ids.push_back(mo->from_loaded_id);
            ModelConfigObject& obj_config = mo->config;

            for (const std::string& opt_key : obj_config.keys()) {
                all_keys.insert(opt_key); // std::set 自动去重
            }

        }

        js["object_ids"] = serialize_with_semicolon(obj_loaded_ids);

        //js["object_enable_support"] = serialize_with_comma(obj_enable_supports);
        // 2. 对每个 key，收集所有对象的值，拼接成 "v1;v2;v3;"
        for (const std::string& key : all_keys) {
            std::string joined;
            for (size_t i = 0; i < objs_on_plate.size(); ++i) {
                ModelConfigObject& obj_config = objs_on_plate[i]->config;
                if (obj_config.has(key))
                    joined += obj_config.opt_serialize(key);
                // 即使没有也要占位
                joined += ";";
            }
            js[key] = joined;
        }

        if(m_analytics_project_info.is_valid) {
            js["cloud_url"] = m_analytics_project_info.url;
            js["cloud_file_id"] = m_analytics_project_info.file_id;
            js["cloud_file_format"] = m_analytics_project_info.file_format;
            js["cloud_model_id"] = m_analytics_project_info.model_id;
            js["cloud_name"] = m_analytics_project_info.name;
        }

        js["operation_date"] = Slic3r::Utils::utc_timestamp(Slic3r::Utils::get_current_time_utc());
        js["app_version"] = GUI_App::format_display_version().c_str();
        js["operating_system"]      = wxGetOsDescription().ToStdString().c_str();

        wxGetApp().track_event("object_print_parameters", js.dump());
    }
    catch (const std::exception& err)
    {
        BOOST_LOG_TRIVIAL(error) << __FUNCTION__<< ": json create " << " got a generic exception, reason = " << err.what();
    } 
    catch (...) {
        BOOST_LOG_TRIVIAL(error) << __FUNCTION__ << ": json create " << " got an unknown exception";
    }
}

void AnalyticsDataUploadManager::uploadSlicePlateEventData()
{
     Plater* plater = wxGetApp().plater();
    Slic3r::AuxiliariesInfo auxiliaries_info = plater->get_auxiliaries_info();

    // only report cubeme project 3mf slice event
    if(auxiliaries_info.get_metadata_application().empty() || auxiliaries_info.get_metadata_project_id().empty())
        return;

    BOOST_LOG_TRIVIAL(warning) << __FUNCTION__ << " cubeme_slice_event";

    json js;
    js["type_code"] = "slice821";
    js["client_id"] = wxGetApp().get_client_id();

    js["application"] = auxiliaries_info.get_metadata_application();
    js["platform"] = auxiliaries_info.get_metadata_platform();
    js["projectInfoId"] = auxiliaries_info.get_metadata_project_id();

    js["app_version"] = GUI_App::format_display_version().c_str();
    js["operating_system"]      = wxGetOsDescription().ToStdString().c_str();
    wxGetApp().track_event("cubeme_slice_event", js.dump());
}

void AnalyticsDataUploadManager::uploadSoftwareLaunchData()
{
    BOOST_LOG_TRIVIAL(warning) << __FUNCTION__ << " start";

    json js;
    js["type_code"] = "slice806";

    js["client_id"] = wxGetApp().get_client_id();
    
    js["startup_duration"] = wxGetApp().get_app_startup_duration();
    js["app_version"] = GUI_App::format_display_version().c_str();
    js["operating_system"]      = wxGetOsDescription().ToStdString().c_str();
    js["launch_date"] = Slic3r::Utils::utc_timestamp(Slic3r::Utils::get_current_time_utc());

    wxGetApp().track_event("software_launch", js.dump());
}

void AnalyticsDataUploadManager::uploadSoftwareCrashData()
{
    BOOST_LOG_TRIVIAL(warning) << __FUNCTION__ << " start";
    json js;
    js["type_code"] = "slice807";
    js["client_id"] = wxGetApp().get_client_id();
    
    js["send_crash_report"] = wxGetApp().get_send_crash_report();
    js["category"] = "client_crash";
    js["action"]   = "show_error_report";
    js["label"]    = "crash_report_dialog";
    js["app_version"] = GUI_App::format_display_version().c_str();
    js["operating_system"]      = wxGetOsDescription().ToStdString().c_str();
    js["system_architecture"] = get_system_architecture();
    js["crash_date"] = Slic3r::Utils::utc_timestamp(Slic3r::Utils::get_current_time_utc());

    wxGetApp().track_event("software_crash", js.dump());
}

void AnalyticsDataUploadManager::uploadSoftwareBadAlloc()
{
    BOOST_LOG_TRIVIAL(warning) << __FUNCTION__ << " start";
    json js;
    js["type_code"] = "slice820";
    js["client_id"] = wxGetApp().get_client_id();

    js["send_crash_report"] = wxGetApp().get_send_crash_report();
    js["category"]          = "client_crash";
    js["action"]            = "show_error_report";
    js["label"]             = "crash_report_dialog";
    js["app_version"]       = GUI_App::format_display_version().c_str();
    js["operating_system"]  = wxGetOsDescription().ToStdString().c_str();
    js["crash_date"]        = Slic3r::Utils::utc_timestamp(Slic3r::Utils::get_current_time_utc());

    wxGetApp().track_event("software_bad_alloc", js.dump());
}


void AnalyticsDataUploadManager::uploadSoftwareCloseData()
{
    BOOST_LOG_TRIVIAL(warning) << __FUNCTION__ << " start";
    json js;
    js["type_code"] = "slice808";
    js["client_id"] = wxGetApp().get_client_id();

    js["usage_duration"] = wxGetApp().get_app_running_duration(); // in minutes
    js["app_version"] = GUI_App::format_display_version().c_str();
    js["operating_system"]      = wxGetOsDescription().ToStdString().c_str();
    js["close_date"] = Slic3r::Utils::utc_timestamp(Slic3r::Utils::get_current_time_utc());

    wxGetApp().track_event("software_close", js.dump());
    BOOST_LOG_TRIVIAL(warning) << __FUNCTION__ << " end";
    boost::log::core::get()->flush();
}

void AnalyticsDataUploadManager::uploadDeviceInfoData()
{
    std::vector<std::string> all_macs = wxGetApp().mainframe->get_printer_mgr_view()->get_all_device_macs();
    if (all_macs.empty())
        return;

    // 统计每种modelName的数量
    std::map<std::string, int> model_count;
    for(const auto& mac : all_macs) {
        nlohmann::json printer_json = DM::DataCenter::Ins().find_printer_by_mac(mac);
        if (!printer_json.is_null()) {
            DM::Device device = DM::Device::deserialize(printer_json);
            if (!device.modelName.empty())
                model_count[device.modelName]++;
        }
    }

    if (model_count.empty())
        return;

    // only upload for one time
    wxGetApp().mainframe->get_printer_mgr_view()->set_finish_upload_device_state(true);

    std::string user_login_id = "";
    if (Slic3r::GUI::wxGetApp().is_login()) {
        Slic3r::GUI::UserInfo user = Slic3r::GUI::wxGetApp().get_user();
        user_login_id = user.userId;
    }

    json js;
    js["type_code"] = "slice812";

    js["client_id"] = wxGetApp().get_client_id();

    // 拼接成 [modelName,count];[modelName,count]; 格式
    std::string device_infos;
    for (const auto& kv : model_count) {
        device_infos += "[" + kv.first + "," + std::to_string(kv.second) + "];";
    }

    js["printer_infos"] = device_infos;

    js["app_version"] = GUI_App::format_display_version().c_str();
    //js["operating_system"]      = wxGetOsDescription().ToStdString().c_str();

    wxGetApp().track_event("device_info", js.dump());
}

void AnalyticsDataUploadManager::uploadAccountDeviceInfoData()
{
    std::string user_account_id = "";
    if (!Slic3r::GUI::wxGetApp().is_login()) {
        return;
    }
    else {
        Slic3r::GUI::UserInfo user = Slic3r::GUI::wxGetApp().get_user();
        user_account_id = user.userId;
    }

    // 获取当前账号下的设备信息
    const AccountDeviceMgr::AccountDeviceInfo& account_device_info = AccountDeviceMgr::getInstance().get_account_device_info();
    auto account_it = account_device_info.account_infos.find(user_account_id);
    if (account_it == account_device_info.account_infos.end()) {
        return ;
    }

    std::map<std::string, int> model_count;

    auto it = account_device_info.account_infos.find(user_account_id);
    if (it != account_device_info.account_infos.end()) {
        const auto& devices = it->second.my_devices;
        for (const auto& device : devices) {
            if (!device.model.empty())
                model_count[device.model]++;
        }
    }

    if(model_count.empty())
        return;
        
    json js;
    js["type_code"] = "slice812";

    js["client_id"] = wxGetApp().get_client_id();

    js["user_login_id"] = user_account_id;

    // 拼接成 [model,count],[model,count] 格式
    std::string device_infos;
    for (auto iter = model_count.begin(); iter != model_count.end(); ++iter) {
        if (iter != model_count.begin()) device_infos += ",";
        device_infos += "[" + iter->first + "," + std::to_string(iter->second) + "]";
    }
    js["printer_infos"] = device_infos;

    js["app_version"] = GUI_App::format_display_version().c_str();
    //js["operating_system"]      = wxGetOsDescription().ToStdString().c_str();

    wxGetApp().track_event("device_info", js.dump());
}

// software first launch (when "AppData\Roaming\Creality" directory first created)
void AnalyticsDataUploadManager::uploadFirstLaunchEventData()
{
    json js;
    js["type_code"] = "slice804";

    js["client_id"] = wxGetApp().get_client_id();

    js["app_version"] = GUI_App::format_display_version().c_str();
    js["operating_system"]      = wxGetOsDescription().ToStdString().c_str();
    js["launch_date"] = Slic3r::Utils::utc_timestamp(Slic3r::Utils::get_current_time_utc());

    wxGetApp().track_event("software_first_launch", js.dump());
}

void AnalyticsDataUploadManager::uploadPreferencesChangedData()
{
    json js;
    js["type_code"] = "slice805";

    js["dark_color_mode"] = wxGetApp().app_config->get("dark_color_mode");
    js["language"] = wxGetApp().app_config->get("language");
    js["region"] = wxGetApp().app_config->get("region");
    js["use_inches"] = wxGetApp().app_config->get("use_inches");
    js["download_path"] = wxGetApp().app_config->get("download_path");
    js["zoom_to_mouse"] = wxGetApp().app_config->get("zoom_to_mouse");
    js["is_arrange"] = wxGetApp().app_config->get("is_arrange");
    js["user_mode"] = wxGetApp().app_config->get("user_mode");
    js["default_page"] = wxGetApp().app_config->get("default_page");
    js["sync_user_preset"] = wxGetApp().app_config->get("sync_user_preset");
    js["user_exp"] = wxGetApp().app_config->get("user_exp");
    js["save_preset_choise"] = wxGetApp().app_config->get("save_preset_choise");
    js["save_project_choise"] = wxGetApp().app_config->get("save_project_choise");
    js["operation_date"] = Slic3r::Utils::utc_timestamp(Slic3r::Utils::get_current_time_utc());
    js["enable_lod"] = wxGetApp().app_config->get("enable_lod");
    js["enable_preview_lod"] = wxGetApp().app_config->get("enable_preview_lod");

    wxGetApp().track_event("preferences_changed", js.dump());
}

// Static: upload slice822 click event
void AnalyticsDataUploadManager::uploadSlice822ClickEvent(const std::string& module, int id)
{
    try {
        nlohmann::json payload;
        payload["type_code"] = "slice822";
        payload["event_type"]      = "click_event";
        payload["function_module"] = module;
        payload["module_id"]       = id;
        payload["app_version"]     = GUI_App::format_display_version().c_str();
        payload["operating_system"] = wxGetOsDescription().ToStdString().c_str();
        payload["timestamp"]       = Slic3r::Utils::utc_timestamp(Slic3r::Utils::get_current_time_utc());

        //nlohmann::json root;
        //root["slice822"] = payload;

        wxGetApp().track_event("click_event", payload.dump());
    } catch (const std::exception& err) {
        BOOST_LOG_TRIVIAL(error) << __FUNCTION__ << ": json create got a generic exception, reason = " << err.what();
    } catch (...) {
        BOOST_LOG_TRIVIAL(error) << __FUNCTION__ << ": json create got an unknown exception";
    }
}

} // namespace GUI
} // namespace Slic3r
