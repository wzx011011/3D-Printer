#include "PrinterMgr.hpp"

#include "../I18N.hpp"
#include "PrinterMgr.hpp"
#include "slic3r/GUI/GUI_App.hpp"
#include "slic3r/GUI/MainFrame.hpp"
#include "libslic3r_version.h"
#include "AppUtils.hpp"
namespace pt = boost::property_tree;
using json = nlohmann::json;

namespace DM {

    class DeviceLoaderV512
    {
    public:
        void Load(DeviceMgr* mgr, boost::filesystem::path& path)
        {
            boost::nowide::ifstream t(path.string());
            std::stringstream buffer;
            buffer << t.rdbuf();

            json data = json::parse(buffer);
            std::vector<std::string> vtGroup;
            if (data.contains("deviceGroupNames"))
            {
                for (auto& group : data["deviceGroupNames"])
                {
                    mgr->AddGroup(group);
                    vtGroup.push_back(group);
                }
            }

            if (data.contains("deviceInfomation"))
            {
                for (auto& device : data["deviceInfomation"])
                {
                    DeviceMgr::Data data;
                    if (device.contains("connectType"))data.connectType = device["connectType"];
                    if (device.contains("modelName"))data.model = device["modelName"];
                    if (device.contains("macAddress"))data.mac = device["macAddress"];
                    if (device.contains("ipAddress"))data.address = device["ipAddress"];
                    if (device.contains("deviceName"))data.name = device["deviceName"];

                    std::string sGroup;
                    if (device.contains("group")) {
                        int groupIndex = device["group"].get<int>() - 1;
                        sGroup = vtGroup[groupIndex];
                    }

                    if (!mgr->IsPrinterExist(data.mac))
                        mgr->AddDevice(sGroup, data);
                }
            }
        }
    };

    class CurrentDeviceCfigV603{
    public:
        static std::string get_current_device_mac(){
            std::string mac;
            boost::filesystem::path device_file = boost::filesystem::path(Slic3r::data_dir()) / "current_device.json";
            if (boost::filesystem::exists(device_file)){

                boost::nowide::ifstream t(device_file.string());
                std::stringstream buffer;
                buffer << t.rdbuf();

                json data = json::parse(buffer);
                if(data.contains("current_device")&&data["current_device"].contains("mac")){
                    mac = data["current_device"]["mac"];
                }
            }

            return mac;
        }
    };

    struct DeviceMgr::priv
    {
        json data;
        std::map<std::string, std::vector<DeviceMgr::Data>> store;
        std::vector<std::string> order;
    };

    DeviceMgr::DeviceMgr() :p(new priv)
    {

    }

    DeviceMgr::~DeviceMgr()
    {

    }

    void DeviceMgr::Load()
    {
        boost::filesystem::path device_file = boost::filesystem::path(Slic3r::data_dir()) / "deviceInfo.json";
        if (!boost::filesystem::exists(device_file))
        {
            boost::filesystem::path device_old_file = boost::filesystem::path(Slic3r::data_dir()).parent_path().parent_path() / "Creative3D/deviceInfo.json";
            if (boost::filesystem::exists(device_old_file))
            {
                DeviceLoaderV512 loader;
                loader.Load(this, device_old_file);
                this->Save();
            }
        }
        else//load from current custom folder
        {
            try{
            boost::nowide::ifstream t(device_file.string());
            std::stringstream buffer;
            buffer << t.rdbuf();
            
            p->data = json::parse(buffer);
            }
            catch (const std::exception& e)
            {
                boost::filesystem::remove(device_file);
                p->data = json::object();
            }
            std::vector<std::string> delIP;
            if (p->data.contains("groups"))
            {
                for (auto& group : p->data["groups"])
                {
                    if (group.contains("list") && !group["list"].is_null())
                    {
                        for (auto jt = group["list"].begin(); jt != group["list"].end(); jt++) {
                            std::vector<std::string> ips = this->GetSamePrinter(jt.value()["mac"].get<std::string>());
                            if (!ips.empty()) {
                                for (auto& ip : ips)
                                    delIP.push_back(ip);
                            }
                        }
                    }
                }
            }

            for (auto& ip : delIP)
            {
                this->RemoveDevice(ip);
            }

#ifdef __WXGTK__
            if (is_uos_system() && p->data.contains("groups")) {
                int total = 0;
                for (auto& group : p->data["groups"]) {
                    if (!group.contains("list") || group["list"].is_null())
                        continue;
                    auto& list = group["list"];
                    if (!list.is_array())
                        continue;
                    if (total >= 20) {
                        list = nlohmann::json::array();
                        continue;
                    }
                    int remaining = 20 - total;
                    if (remaining <= 0) {
                        list = nlohmann::json::array();
                        continue;
                    }
                    if (static_cast<int>(list.size()) > remaining) {
                        nlohmann::json new_list = nlohmann::json::array();
                        for (int i = 0; i < remaining; ++i)
                            new_list.push_back(list[i]);
                        list = new_list;
                        total = 20;
                    } else {
                        total += static_cast<int>(list.size());
                    }
                }
            }
#endif
        }

        if (p->data.empty())
        {
            this->AddGroup("New Group1");
        }

        // can set current device is empty now
        /*if(this->GetCurrentDevice().empty()){
            std::string mac = CurrentDeviceCfigV603::get_current_device_mac();
            if(!mac.empty())
            {
                this->SetCurrentDevice(mac);
            }
        }*/

        //clear not use default group
        std::vector<int> remove_group_ids;
        int index = 0;
        for (auto& group : p->data["groups"]){
            std::string name = group["group"];
            if(name == "Default" && group.contains("list") && group["list"].is_null()){
                remove_group_ids.push_back(index);
            }

            index++;
        }

        for(int i =remove_group_ids.size()-1; i>=0 ;i-- ){
             p->data["groups"].erase(remove_group_ids[i]);
        }

        remove_group_ids.clear();
        index = 0;
        int cnt = 0;
        int null_cnt = 0;
        for (auto& group : p->data["groups"]) {
            std::string name = group["group"];
            if (name == "Default") {
                if(!group.contains("list")){
                    null_cnt++;
                    remove_group_ids.push_back(index);
                }

                cnt++;
            }

            index++;
        }

        int n = cnt==null_cnt?1:0;
        for (int i = remove_group_ids.size()-1;  i >= n; i--) {//Just keep one
            p->data["groups"].erase(remove_group_ids[i]);
        }

        this->Save();
        //  CLEAR END
    }

    void DeviceMgr::Save()
    {
        boost::filesystem::path device_file = boost::filesystem::path(Slic3r::data_dir()) / "deviceInfo.json";

        boost::nowide::ofstream c;
        c.open(device_file.string(), std::ios::out | std::ios::trunc);
        c << std::setw(4) << p->data << std::endl;

    }
    void DeviceMgr::UpdateDevice(std::string mac, Data& data)
    {
        for (auto& group : p->data["groups"])
        {
            int index = 0;
            for (auto& item : group["list"])
            {
                std::string omac = item["mac"];
                if (mac == omac)
                {
                    item["mac"] = data.mac;
                    item["address"] = data.address;
                    item["model"] = data.model;
                    item["connectType"] = data.connectType;
                    this->Save();
                    return;
                }
            }
        }
        std::string ip = data.address;
        for (auto& group : p->data["groups"])
        {
            int index = 0;
            for (auto& item : group["list"])
            {
                std::string address = item["address"];
                if (ip == address)
                {
                    item["mac"] = data.mac;
                    item["address"] = data.address;
                    item["model"] = data.model;
                    item["connectType"] = data.connectType;
                    this->Save();
                    return;
                }
            }
        }
    }
    void DeviceMgr::AddDevice(std::string group, Data& data)
    {
        if (!this->IsGroupExist(group)) {
            this->AddGroup(group, false);
        }

        nlohmann::json item;
        item["address"] = data.address;
        item["mac"] = data.mac;
        item["model"] = data.model;
        item["name"] = data.name;
        item["connectType"] = data.connectType;
        item["oldPrinter"] = data.oldPrinter;
        item["deviceUI"] = data.deviceUI;

        item["moonrakerPort"] = data.moonrakerPort;
        item["fluiddPort"] = data.fluiddPort;
        item["mainsailPort"] = data.mainsailPort;

        if (data.connectType == 1001) 
        {
            item["apiKey"] = data.apiKey;
            item["hostType"] = data.hostType;
            item["caFile"] = data.caFile;
            item["ignoreCertRevocation"] = data.ignoreCertRevocation;
        }

        for (auto& g : p->data["groups"])
        {
            if (g["group"] == group)
            {
                if (!g.contains("list"))
                {
                    g["list"].push_back(item);
                }
                else
                {
                    if(g["list"].is_null()){
                        g["list"] = nlohmann::json::array();
                        g["list"].push_back(item);
                    }
                    else
                    {
                        g["list"].insert(g["list"].begin(), item);
                    }
                }

                this->Save();
                break;
            }
        }
    }

    void DeviceMgr::RemoveDevice(std::string address)
    {
        for (auto& group : p->data["groups"])
        {
            int index = 0;
            for (auto& item : group["list"])
            {
                std::string ip = item["address"];
                if (ip == address)
                {
//                     std::string mac = item["mac"];
//                     if(mac == this->GetCurrentDevice())
//                     {
//                         this->SetCurrentDevice("");
//                     }
                    group["list"].erase(index);
                    this->Save();
                    return;
                }
                index++;
            }
        }
    }

    void DeviceMgr::EditDeiveName(std::string address, std::string name)
    {
        for (auto& group : p->data["groups"])
        {
            int index = 0;
            for (auto& item : group["list"])
            {
                std::string ip = item["address"];
                if (ip == address)
                {
                    item["name"] = name;
                    this->Save();
                    return;
                }
                index++;
            }
        }
    }

    void DeviceMgr::AddGroup(std::string name,  bool is_save)
    {
        auto& groups = p->data["groups"];

        json item;
        item["group"] = name;
        groups.push_back(item);

        if (is_save){
            this->Save();
        }
    }

    void DeviceMgr::RemoveGroup(std::string name)
    {
        int index = 0;
        for (auto& group : p->data["groups"])
        {
            if (group["group"] == name)
            {
                if(group.contains("list"))
                {
                    for (auto& device : group["list"]) {
                        std::string mac = device["mac"];
                        if(mac == this->GetCurrentDevice()){
                            this->SetCurrentDevice("");
                        }
                    }
                }

                p->data["groups"].erase(index);
                this->Save();
                return;
            }

            index++;
        }
    }

    void DeviceMgr::EditGroupName(std::string name, std::string nameNew)
    {
        int index = 0;
        for (auto& group : p->data["groups"])
        {
            if (group["group"] == name)
            {
                group["group"] = nameNew;
                this->Save();
                return;
            }

            index++;
        }
    }
    void DeviceMgr::remove2FirstGroup(std::string name) {
        auto& groupList = p->data["groups"];
        if (name == "" || groupList.size() < 2) {
            return;
        }
        auto& f = groupList.front();
        auto& g = (f["group"] == name) ? groupList[1] : f;
        if (g["list"].is_null()) {
            g["list"] = nlohmann::json::array();
        }
        for (auto& group : groupList) {
            if (group["group"] == name) {
                if (group.contains("list")) {
                    for (auto& device : group["list"]) {
                        g["list"].insert(g["list"].begin(), device);
                    }
                }
                break;
            }
        }
        RemoveGroup(name);
    }

    void DeviceMgr::move2Group(std::string originGroup, std::string targetGroup, std::string address)
    {
        auto& groupList = p->data["groups"];
        if (address == "" || originGroup == "" || targetGroup == "") {
            return;
        }

        json* p = nullptr;
        for (auto& group : groupList) {
            if (group["group"] == targetGroup) {
                p = &group;
                break;
            }
        }
        if (p == nullptr) {
            return;
        }
        auto& g = *p;
        for (auto& group : groupList) {
            if (group["group"] == originGroup) {
                if (group.contains("list")) {
                    int index = -1;
                    for (auto& device : group["list"]) {
                        index++;
                        if (device["address"] == address) {
                            if (g["list"].is_null()) {
                                g["list"] = nlohmann::json::array();
                            }
                            g["list"].insert(g["list"].begin(), device);
                            group["list"].erase(index);
                            this->Save();
                            return;
                        }
                    }
                }
                break;
            }
        }
    }

    bool groupSort(const json& a, const json& b, std::vector<std::string> order)
    {
        auto itA = std::find(order.begin(), order.end(), a["group"].get<std::string>());
        auto itB = std::find(order.begin(), order.end(), b["group"].get<std::string>());

        return itA < itB;
    }

    void DeviceMgr::sortGroup(std::vector<std::string> order)
    {
        auto& groupList = p->data["groups"];
        std::sort(groupList.begin(), groupList.end(), [&order](const json& a, const json& b) { return groupSort(a, b, order); });
        this->Save();
    }

    void DeviceMgr::SetMergeState(bool state)
    {
        p->data["mergeState"] = state;
        this->Save();
    }

    bool DeviceMgr::IsMergeState()
    {
        bool mergeState = false;
        if (p->data.contains("mergeState")) {
            mergeState = p->data["mergeState"].get<bool>();
        }

        return mergeState;
    }

    nlohmann::json DeviceMgr::GetData()
    {
        return p->data;
    }

    void DeviceMgr::Get(std::map<std::string, std::vector<DeviceMgr::Data>>& store, std::vector<std::string>& order)
    {
        for (auto it = p->data["groups"].begin(); it != p->data["groups"].end(); it++)
        {
            auto& group = it.value();
            std::string name = group["group"];
            store[name];
            if (group.contains("list"))
            {
                for (auto jt = group["list"].begin(); jt != group["list"].end(); jt++)
                {
                    Data data;
                    data.address = jt.value()["address"].get<std::string>();
                    data.connectType = jt.value()["connectType"].get<int>();
                    data.mac = jt.value()["mac"].get<std::string>();
                    data.model = jt.value()["model"].get<std::string>();
                    data.name = jt.value()["name"].get<std::string>();

                    store[name].push_back(data);
                }
            }

            if (std::find(order.begin(), order.end(), name) == order.end())
                order.push_back(name);
        }
    }

    bool DeviceMgr::IsGroupExist(std::string name)
    {
        for (auto& group : p->data["groups"])
        {
            if (group["group"] == name)
                return true;
        }

        return false;
    }

    bool DeviceMgr::IsPrinterExist(std::string mac)
    {
        if (p->data.contains("groups"))
        {
            for (auto& group : p->data["groups"])
            {
                if (group.contains("list"))
                {
                    for (auto jt = group["list"].begin(); jt != group["list"].end(); jt++) {
                        if (mac == jt.value()["mac"].get<std::string>())
                            return true;
                    }
                }
            }
        }

        return false;
    }

    std::vector<std::string> DeviceMgr::GetSamePrinter(std::string mac)
    {
        std::vector<std::string> vt;
        int cnt = 0;
        if (p->data.contains("groups"))
        {
            for (auto& group : p->data["groups"])
            {
                if (group.contains("list"))
                {
                    for (auto jt = group["list"].begin(); jt != group["list"].end(); jt++) {
                        if (mac == jt.value()["mac"].get<std::string>())
                        {
                            if (cnt != 0)
                            {
                                std::string ip = jt.value()["address"].get<std::string>();
                                vt.push_back(ip);
                            }
                            cnt++;
                        }
                    }
                }
            }
        }
        return vt;
    }

    void DeviceMgr::SetCurrentDevice(std::string mac)
    {
        /*if (mac!=""&&!IsPrinterExist(mac)) { // now can set empty mac is current deivce 
            return;
        }*/
        auto& node = p->data["current_device"];

        json item;
        item["mac"] = mac;

        node = item;

        this->Save();
    }

    std::string DeviceMgr::GetCurrentDevice()
    {
        if(p->data.contains("current_device") && p->data["current_device"].contains("mac"))
            return p->data["current_device"]["mac"];

        return std::string();
    }

    DeviceMgr& DeviceMgr::Ins()
    {
        static DeviceMgr mgr;
        return mgr;
    }

}
