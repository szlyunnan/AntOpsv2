#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os, sys, subprocess, socket
import re

def collect():
    filter_keys = ['Manufacturer','Serial Number','Product Name','UUID','Wake-up Type']
    raw_data = {}
    for key  in filter_keys:
        try:
            result = subprocess.check_output("dmidecode -t system|grep '%s'" % key, shell=True)
            result = result.strip()
            result_to_list = result.split(':')
            if len(result_to_list) > 1:
                raw_data[key] = result_to_list[1].strip()
            else:
                raw_data[key] = result_to_list[-1]
            pass
        except Exception as E:
            print(E)
            raw_data[key] = -2

    data = {"asset_type": 'server'}
    data['manufactory'] = raw_data['Manufacturer']
    data['sn'] = raw_data['Serial Number']
    data['model'] = raw_data['Product Name']
    data['uuid'] = raw_data['UUID']
    data['wake_up_type'] = raw_data['Wake-up Type']
    data.update(cpuinfo())
    data.update(osinfo())

def cpuinfo():
    cpu_file = "/proc/cpuinfo"
    raw_data = {
        "cpu_model": "grep 'model name' %s | head -n 1" % cpu_file,
        "cpu_count": "grep 'processor' %s | wc -l" % cpu_file,   # 逻辑CPU个数
        "cpu_core_count": "grep 'core id' %s | sort | uniq | wc -l" % cpu_file, # CPU 核数
    }
    for k, cmd in raw_data:
        try:
            result = subprocess.check_output(cmd, shell=True)
            raw_data[k] = result.strip()
        except ValueError as E:
            print(E)
    data = {
        "cpu_count": raw_data["cpu_count"],
        "cpu_core_count": raw_data["cpu_core_count"]
    }
    cpu_model = raw_data["cpu_model"].split(':')
    if cpu_model > 1:
        data["cpu_model"] = cpu_model[1].strip()
    else:
        data["cpu_model"] = -1
    return data

def osinfo():
    release = subprocess.check_output("lsb_release -d", shell=True).split(":")
    data_dic = {
        "os_release": release[1].strip() if len(release) > 1 else None,
        "os_type": "linux",
    }
    return data_dic

def osinfo():
    distributor = subprocess.getoutput(" lsb_release -a|grep 'Distributor ID'").split(":")
    release  = subprocess.getoutput(" lsb_release -a|grep Description").split(":")
    data_dic ={
        "os_distribution": distributor[1].strip() if len(distributor)>1 else None,
        "os_release":release[1].strip() if len(release)>1 else None,
        "os_type": "linux",
    }
    return data_dic

def diskinfo():
    obj = DiskPlugin()
    return obj.linux()

def nicinfo():
    raw_data = subprocess.getoutput("ifconfig -a")
    raw_data= raw_data.split("\n")
    nic_dic = {}
    next_ip_line = False
    last_mac_addr = None
    for line in raw_data:
        if next_ip_line:
            next_ip_line = False
            nic_name = last_mac_addr.split()[0]
            mac_addr = last_mac_addr.split("HWaddr")[1].strip()
            raw_ip_addr = line.split("inet addr:")
            raw_bcast = line.split("Bcast:")
            raw_netmask = line.split("Mask:")
            if len(raw_ip_addr) > 1:
                ip_addr = raw_ip_addr[1].split()[0]
                network = raw_bcast[1].split()[0]
                netmask =raw_netmask[1].split()[0]
            else:
                ip_addr = None
                network = None
                netmask = None
            if mac_addr not in nic_dic:
                nic_dic[mac_addr] = {'name': nic_name,
                                     'macaddress': mac_addr,
                                     'netmask': netmask,
                                     'network': network,
                                     'bonding': 0,
                                     'model': 'unknown',
                                     'ipaddress': ip_addr,
                                     }
            else: #mac already exist , must be boding address
                if '%s_bonding_addr' %(mac_addr) not in nic_dic:
                    random_mac_addr = '%s_bonding_addr' %(mac_addr)
                else:
                    random_mac_addr = '%s_bonding_addr2' %(mac_addr)
                nic_dic[random_mac_addr] = {'name': nic_name,
                                     'macaddress':random_mac_addr,
                                     'netmask': netmask,
                                     'network': network,
                                     'bonding': 1,
                                     'model': 'unknown',
                                     'ipaddress': ip_addr,
                                     }
        if "HWaddr" in line:
            #print line
            next_ip_line = True
            last_mac_addr = line
    nic_list= []
    for k,v in nic_dic.items():
        nic_list.append(v)
    return {'nic':nic_list}

def raminfo():
    raw_data = subprocess.getoutput(" dmidecode -t 17")
    raw_list = raw_data.split("\n")
    raw_ram_list = []
    item_list = []
    for line in raw_list:
        if line.startswith("Memory Device"):
            raw_ram_list.append(item_list)
            item_list =[]
        else:
            item_list.append(line.strip())
    ram_list = []
    for item in raw_ram_list:
        item_ram_size = 0
        ram_item_to_dic = {}
        for i in item:
            data = i.split(":")
            if len(data) ==2:
                key,v = data
                if key == 'Size':
                    if  v.strip() != "No Module Installed":
                        ram_item_to_dic['capacity'] =  v.split()[0].strip() #e.g split "1024 MB"
                        item_ram_size = int(v.split()[0])
                    else:
                        ram_item_to_dic['capacity'] =  0
                if key == 'Type':
                    ram_item_to_dic['model'] =  v.strip()
                if key == 'Manufacturer':
                    ram_item_to_dic['manufactory'] =  v.strip()
                if key == 'Serial Number':
                    ram_item_to_dic['sn'] =  v.strip()
                if key == 'Asset Tag':
                    ram_item_to_dic['asset_tag'] =  v.strip()
                if key == 'Locator':
                    ram_item_to_dic['slot'] =  v.strip()
        if item_ram_size == 0:  # empty slot , need to report this
            pass
        else:
            ram_list.append(ram_item_to_dic)
    raw_total_size = subprocess.getoutput("cat /proc/meminfo|grep MemTotal ").split(":")
    ram_data = {'ram':ram_list}
    if len(raw_total_size) == 2:#correct
        total_mb_size = int(raw_total_size[1].split()[0]) / 1024
        ram_data['ram_size'] =  total_mb_size
    return ram_data





class DiskPlugin(object):
    def linux(self):
        result = {'physical_disk_driver':[]}
        try:
            script_path = os.path.dirname(os.path.abspath(__file__))
            shell_command = " %s/MegaCli  -PDList -aALL" % script_path
            output = subprocess.getstatusoutput(shell_command)
            result['physical_disk_driver'] = self.parse(output[1])
        except Exception as e:
            result['error'] = e
        return result
    def parse(self,content):
        '''
        解析shell命令返回结果
        :param content: shell 命令结果
        :return:解析后的结果
        '''
        response = []
        result = []
        for row_line in content.split("\n\n\n\n"):
            result.append(row_line)
        for item in result:
            temp_dict = {}
            for row in item.split('\n'):
                if not row.strip():
                    continue
                if len(row.split(':')) != 2:
                    continue
                key,value = row.split(':')
                name =self.mega_patter_match(key);
                if name:
                    if key == 'Raw Size':
                        raw_size = re.search('(\d+\.\d+)',value.strip())
                        if raw_size:
                            temp_dict[name] = raw_size.group()
                        else:
                            raw_size = '0'
                    else:
                        temp_dict[name] = value.strip()
            if temp_dict:
                response.append(temp_dict)
        return response

    def mega_patter_match(self,needle):
        grep_pattern = {'Slot':'slot', 'Raw Size':'capacity', 'Inquiry':'model', 'PD Type':'iface_type'}
        for key,value in grep_pattern.items():
            if needle.startswith(key):
                return value
        return False

if __name__=="__main__":
    print(DiskPlugin().linux())








def collect():
    filter_keys = ['Manufacturer','Serial Number','Product Name','UUID','Wake-up Type']
    raw_data = {}
    for key in filter_keys:
        try:
            cmd_res = commands.getoutput(" dmidecode -t system|grep '%s'" %key)
            cmd_res = cmd_res.strip()
            res_to_list = cmd_res.split(':')
            if len(res_to_list)> 1:
                raw_data[key] = res_to_list[1].strip()
            else:
                raw_data[key] = -1
        except Exception as e:
            print(e)
            raw_data[key] = -2
    data = {"asset_type": 'server'}
    data['manufactory'] = raw_data['Manufacturer']
    data['sn'] = raw_data['Serial Number']
    data['model'] = raw_data['Product Name']
    data['uuid'] = raw_data['UUID']
    data['wake_up_type'] = raw_data['Wake-up Type']
    data.update(cpuinfo())
    data.update(osinfo())
    data.update(raminfo())
    data.update(nicinfo())
    data.update(diskinfo())
    data.update(hostnameinfo())
    return data
def diskinfo():
    obj = DiskPlugin()
    return obj.linux()
import psutil
def nicinfo():
    netcard_info = []
    info = psutil.net_if_addrs()
    for k,v in info.items():
        for item in v:
            if item[0] == 2 and not item[1]=='127.0.0.1':
                netcard_info.append((k,item[1]))
    return {'nic': netcard_info}
def hostnameinfo():
    hostname = socket.gethostname()
    return {'hostname': hostname}
def raminfo():
    raw_data = commands.getoutput(" dmidecode -t 17")
    raw_list = raw_data.split("\n")
    raw_ram_list = []
    item_list = []
    for line in raw_list:
        if line.startswith("Memory Device"):
            raw_ram_list.append(item_list)
            item_list =[]
        else:
            item_list.append(line.strip())
    ram_list = []
    for item in raw_ram_list:
        item_ram_size = 0
        ram_item_to_dic = {}
        for i in item:
            data = i.split(":")
            if len(data) ==2:
                key,v = data
                if key == 'Size':
                    if  v.strip() != "No Module Installed":
                        ram_item_to_dic['capacity'] =  v.split()[0].strip() #e.g split "1024 MB"
                        item_ram_size = int(v.split()[0])
                    else:
                        ram_item_to_dic['capacity'] =  0
                if key == 'Type':
                    ram_item_to_dic['model'] =  v.strip()
                if key == 'Manufacturer':
                    ram_item_to_dic['manufactory'] =  v.strip()
                if key == 'Serial Number':
                    ram_item_to_dic['sn'] =  v.strip()
                if key == 'Asset Tag':
                    ram_item_to_dic['asset_tag'] =  v.strip()
                if key == 'Locator':
                    ram_item_to_dic['slot'] =  v.strip()
        if item_ram_size == 0:  # empty slot , need to report this
            pass
        else:
            ram_list.append(ram_item_to_dic)
    raw_total_size = commands.getoutput("cat /proc/meminfo|grep MemTotal ").split(":")
    ram_data = {'ram':ram_list}
    if len(raw_total_size) == 2:#correct
        total_mb_size = int(raw_total_size[1].split()[0]) / (1024.0 ** 2)
        ram_data['ram_size'] = "%.2f G" % total_mb_size
    return ram_data
def osinfo():
    distributor = commands.getoutput(" lsb_release -a|grep 'Distributor ID'").split(":")
    release  = commands.getoutput(" lsb_release -a|grep Description").split(":")
    data_dic ={
        "os_distribution": distributor[1].strip() if len(distributor)>1 else None,
        "os_release":release[1].strip() if len(release)>1 else None,
        "os_type": "linux",
    }
    return data_dic
def cpuinfo():
    base_cmd = 'cat /proc/cpuinfo'
    raw_data = {
        'cpu_model' : "%s |grep 'model name' |head -1 " % base_cmd,
        'cpu_count' :  "%s |grep  'processor'|wc -l " % base_cmd,
        'cpu_core_count' : "%s |grep 'cpu cores' |awk -F: '{SUM +=$2} END {print SUM}'" % base_cmd,
    }
    for k,cmd in raw_data.items():
        try:
            cmd_res = commands.getoutput(cmd)
            raw_data[k] = cmd_res.strip()
        except ValueError as e:
            print(e)
    data = {
        "cpu_count" : raw_data["cpu_count"],
        "cpu_core_count": raw_data["cpu_core_count"]
        }
    cpu_model = raw_data["cpu_model"].split(":")
    if len(cpu_model) >1:
        data["cpu_model"] = cpu_model[1].strip()
    else:
        data["cpu_model"] = -1
    return data
class DiskPlugin(object):
    def __init__(self):
        pass
    def humanize_bytes(self, bytesize, precision=0):
        abbrevs = (
            (10 ** 15, 'PB'),
            (10 ** 12, 'TB'),
            (10 ** 9, 'GB'),
            (10 ** 6, 'MB'),
            (10 ** 3, 'kB'),
            (1, 'bytes')
        )
        if bytesize == 1:
            return '1 byte'
        for factor, suffix in abbrevs:
            if bytesize >= factor:
                break
        return '%.*f%s' % (precision, round(float(bytesize) / factor), suffix)
    def linux(self):
        with open('/proc/partitions', 'r') as dp:
            result = {'physical_disk_driver': []}
            for disk in dp:
                one_res = {}
                if re.search(r'[s,h,v]d[a-z]\n', disk):
                    blknum = disk.strip().split(' ')[-2]
                    dev = disk.strip().split(' ')[-1]
                    size = int(blknum) * 1024
                    consist = self.humanize_bytes(size).strip()
                    one_res[dev] = consist
                    result["physical_disk_driver"].append(one_res)
        return result
if __name__ == "__main__":
    data = diskinfo()
    print(data)
