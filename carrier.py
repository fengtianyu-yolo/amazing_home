
import os
import time
import shutil
from enum import Enum
import multiprocessing
import multiprocessing.managers
import sqlite3
import time

class folder_info:
    # folder_name = "" # 文件夹名字
    # update_time = -1 # 文件夹更新时间
    # folder_size = 0 # 文件夹数据大小
    # file_count = 0 # 文件夹中文件数量
    # folder_local_path = ""
    
    def __init__(self, folder_name, update_time, folder_size, file_count, folder_local_path) -> None:
        self.folder_name = folder_name
        self.update_time = update_time
        self.folder_size = folder_size
        self.file_count = file_count
        self.folder_local_path = folder_local_path

    def __str__(self) -> str:
        return "filename="+self.folder_name+"; update_time="+self.update_time+"; folder_size="+self.folder_size
    
    def is_equal(self, folder) -> bool:
        if not self.folder_name == folder.folder_name:
            return False
        if not self.folder_size == folder.folder_size:
            return False
        if not self.update_time == folder.update_time:
            return False
        return True
    
    def __eq__(self, __value: object) -> bool:        
        if isinstance(__value, folder_info):
            if not self.folder_name == __value.folder_name:
                return False
            if not self.folder_size == __value.folder_size:
                return False
            if not self.update_time == __value.update_time:
                return False
            return True
        else:
            return False


class carrier_info():
    def __init__(self) -> None:
        self.state = 0 # 0=idle 1=working
        self.process = 0 # 拷贝进度
        self.start_time = 0 # 开始时间
        self.duration = 0
        

class carrier:
    
    local_root_path = "/Users/fengtianyu/Downloads"
    remote_root_path = "/Users/fengtianyu/Desktop/Target"
    db_path = "/Users/fengtianyu/.carrier.db"

    def __init__(self) -> None:
        # 连接数据库
        self.connection = sqlite3.connect(carrier.db_path)
        self.cursor = self.connection.cursor()
        # id, state当前状态，process 进度，start_time 开始时间，duration 持续时长 默认-1，folder_list 本次移动的文件夹 
        self.cursor.execute('create table if not exists history(ID integer primary key AUTOINCREMENT, STATE integer, PROCESS integer default 0, START_TIME time, DATA_SIZE integer default 0, DURATION integer default -1, FOLDERS text)')
        

    def load_folders(self, root_path) -> dict:
        ### 获取路径下的所有folder对象
        folder_dict = {}
        # 读取目录下的所有文件夹信息
        file_list = os.listdir(root_path)
        # 遍历当前文件夹
        for file in file_list:    
            file_path = os.path.join(root_path, file)
            if not os.path.isdir(file_path):
                continue
            # 获取文件夹信息
            folderInfo = os.stat(file_path)
            # 获取最近修改时间
            folder_mtime = folderInfo.st_mtime
            # 获取文件夹的大小
            folder_size = folderInfo.st_size
            # 生成 folder对象
            folder = folder_info(file, folder_mtime, folder_size, 1, file_path)
            folder_dict[file] = folder
            # print(file_path, folder_mtime, folder_size, 1, file_path)
        return folder_dict
            
    def get_changed_list(self) -> []:
        
        # 本地新增的文件夹
        # 字典的keys -> array -> set 
        local_keys = list(self.local_folder_dict.keys())
        local_keys_set = set(local_keys)
        remote_keys = list(self.remote_folder_dict.keys())
        remote_keys_set = set(remote_keys)
        # 获取本地新增的key 
        new_add_folders = local_keys_set.difference(remote_keys_set)
        

        # 本地有改动的文件夹
        # 先拿到所有都存在的文件夹
        intersection_folders = local_keys_set.intersection(remote_keys_set)
        changed_folders: [folder_info] = []
        # 遍历这个集合，检查文件夹信息是否有变化 
        for folder in iter(intersection_folders):
            local_folder = self.local_folder_dict[folder]
            remote_folder = self.remote_folder_dict[folder]
            if not local_folder == remote_folder:
                changed_folders.append(local_folder)
        
        result_folders = changed_folders + list(new_add_folders)
        return result_folders

    def addlog(self):
        current_time = int(time.time())                
        folder_names = ",".join(self.folder_list)
        data_size = 0
        sql = "insert into history (state, process, start_time, data_size, folders) values ({state}, {process}, {start_time}, {data_size}, '{folders}');".format(state=1, process=0, start_time=current_time, data_size=data_size, folders=folder_names)
        print(sql)
        self.cursor.execute(sql)
        self.connection.commit()

    def transfor_data(self):
        # 向其他进程发送数据 https://segmentfault.com/q/1010000043232986 ； https://zhuanlan.zhihu.com/p/60055297 
        # 写入日志 start_time=now, state=1, process=0.1, folder_list=[], 
        self.addlog()
        # 开始拷贝 ,开一个子线程
        for folder_name in self.folder_list:
            folder = self.local_folder_dict[folder_name]
            shutil.copytree(folder.folder_local_path, self.remote_root_path)
        
        # 开一个定时器 查询进度 


    def query_process():
        pass
    
    def run(self):        
        # 拿到本地的所有文件夹
        self.local_folder_dict = self.load_folders(carrier.local_root_path)
        # 拿到远端的所有文件夹
        self.remote_folder_dict = self.load_folders(carrier.remote_root_path)
        # 拿到所有需要同步的文件夹的名字
        self.folder_list = self.get_changed_list()
        # 如果对比没有差异，本次不需要同步。记录日志。
        if self.folder_list.count == 0:
            # 写入日志表 
            return
        
        # 发送系统通知
        #os.system('osascript -e \'display notification "开始备份..." with title "Carrier" \'')
        
        # 开始进行数据同步  
        self.transfor_data()
        

if __name__ == '__main__':
    carrier = carrier()
    carrier.run()

