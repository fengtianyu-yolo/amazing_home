
import os
import time
import shutil
from enum import Enum
import multiprocessing
import multiprocessing.managers
import sqlite3
import time
from threading import Timer
import threading
import sched

class folder_info:
    # folder_name = "" # 文件夹名字
    # update_time = -1 # 文件夹更新时间
    # folder_size = 0 # 文件夹数据大小
    # file_count = 0 # 文件夹中文件数量
    # folder_local_path = ""
    
    def __init__(self, folder_name, update_time, folder_size, format_folder_size, file_count, folder_local_path) -> None:
        self.folder_name = folder_name
        self.update_time = update_time
        self.folder_size = folder_size
        self.format_folder_size = format_folder_size
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
    
    local_root_path = "/Users/fengtianyu/Library/Developer/Xcode/DerivedData"
    remote_root_path = "/Users/fengtianyu/Desktop/Target"
    db_path = "/Users/fengtianyu/.carrier.db"

    def __init__(self) -> None:
        # 连接数据库
        self.connection = sqlite3.connect(carrier.db_path)
        self.cursor = self.connection.cursor()
        # id, state当前状态，process 进度，start_time 开始时间，duration 持续时长 默认-1，folder_list 本次移动的文件夹 
        self.cursor.execute('create table if not exists history(ID integer primary key AUTOINCREMENT, STATE integer, PROCESS integer default 0, START_TIME time, DATA_SIZE integer default 0, DURATION integer default -1, FOLDERS text)')
        
    
    def data_size_format(self, size) -> str:
        if size > (1024 * 1024 * 1024): # GB 
            result = float(size) / 1024.0 / 1024.0 / 1024.0
            format_result = round(result, 2)
            return "{} GB".format(format_result)
        elif size > (1024 * 1024): # MB
            result = float(size) / 1024.0 / 1024.0
            format_result = round(result, 2)
            return "{} MB".format(format_result)
        elif size > 1024: # KB
            result = float(size) / 1024.0
            format_result = round(result, 2)
            return "{} KB".format(format_result)
        else:
            return "{} B".format(size)


    def caculate_folder_size(self, path) -> (str, int):        
        """
        统计文件夹的数据大小 
        Returns:
            str: 格式化的大小
            int: 数据大小 单位是B
        """
        size = 0
        for root, dir, files in os.walk(path):
            # 先拿到当前目录先所有文件的大小
            folder_size = 0
            for file in files:
                file_path = root + "/" + file
                if os.path.islink(file_path):
                    #print("{}是一个链接".format(file_path))
                    continue
                file_size = os.path.getsize(file_path)
                size += file_size
                folder_size += file_size
            # print("root = {}, size= {}".format(root, self.data_size_format(folder_size))) # 打印根目录下的每个文件夹的大小

        return (self.data_size_format(size=size), size)


    def load_folders(self, root_path) -> (dict, int):
        """
        获取路径下的所有folder对象 
        只拿一级目录的
        """
        print("获取{}路径下所有文件夹 ... ".format(root_path))
        folder_dict = {}
        # 读取目录下的所有文件夹信息
        file_list = os.listdir(root_path)
        total_size = 0
        # 遍历当前文件夹
        for file in file_list:    
            file_path = os.path.join(root_path, file)
            if not os.path.isdir(file_path):
                continue
            # 获取文件夹信息
            folderInfo = os.stat(file_path)
            # 获取最近修改时间
            folder_mtime = folderInfo.st_mtime
            # 计算文件夹的大小
            folder_size_info = self.caculate_folder_size(file_path)
            # 生成 folder对象
            folder = folder_info(file, folder_mtime, folder_size=folder_size_info[1], format_folder_size=folder_size_info[0], file_count=1, folder_local_path=file_path)
            folder_dict[file] = folder
            total_size += folder_size_info[1]
            # print(file_path, folder_mtime, folder_size, 1, file_path)
        
        
        format_total_size = self.data_size_format(total_size)
        print("文件夹加载完成，所有需要拷贝的文件夹大小 = {}".format(format_total_size))

        return (folder_dict, total_size)
            

    def get_changed_list(self) -> []:
        """
        获取所有需要备份的文件夹列表
        """

        # 获取本地所有文件夹的名字，放到set中
        local_keys = list(self.local_folder_dict.keys())
        local_keys_set = set(local_keys)
        # 获取远端的所有文件夹的名字，放到set中
        remote_keys = list(self.remote_folder_dict.keys())
        remote_keys_set = set(remote_keys)

        # 获取本地新增的文件夹的名字 
        new_add_folders = local_keys_set.difference(remote_keys_set)
        
        # 本地有改动的文件夹
        # 先拿到在两端都有的文件夹
        intersection_folders = local_keys_set.intersection(remote_keys_set)
        changed_folders: [str] = [] # 存放所有有修改的文件夹的名字
        unchanged_folders: [str] = [] # 存放所有没有修改的文件夹
        # 遍历这个集合，检查文件夹信息是否有变化 
        for folder in iter(intersection_folders):
            # 根据文件夹名字，获取本地的文件夹对象
            local_folder_model = self.local_folder_dict[folder]
            # 根据文件夹名字，获取远端的文件夹对象
            remote_folder_model = self.remote_folder_dict[folder]
            # 如果两个文件夹对象的数据一致，则不需要备份
            if local_folder_model == remote_folder_model:                
                unchanged_folders.append(folder)
            else:
                changed_folders.append(folder)
        
        print("新增加的文件夹列表：{}".format(",".join(list(new_add_folders))))
        print("有修改的文件夹列表：{}".format(",".join(list(changed_folders))))
        print("无修改的文件夹列表：{}".format(",".join(list(unchanged_folders))))
        result_folders = changed_folders + list(new_add_folders)
        return result_folders



    def addlog(self):
        """
        把拷贝历史添加到数据库
        """
        print("日志写入到数据库 ... ")
        current_time = int(time.time())                
        folder_names = ",".join(self.folder_list)
        data_size = 0
        sql = "insert into history (state, process, start_time, data_size, folders) values ({state}, {process}, {start_time}, {data_size}, '{folders}');".format(state=1, process=0, start_time=current_time, data_size=data_size, folders=folder_names)
        print(sql)
        self.cursor.execute(sql)
        self.connection.commit()



    def transfor_data(self):
        """
        开始备份数据
        """
        # 写入日志 start_time=now, state=1, process=0.1, folder_list=[], 
        print("开始数据传输 ... ")
        self.addlog()
        # 开一个定时器 查询进度 
        self.start_timer()

        # 开始拷贝 ,开一个子线程
        for folder_name in self.folder_list:
            folder = self.local_folder_dict[folder_name] # 拿到文件夹对象
            remote_path = self.remote_root_path + "/" + folder_name
            print("数据同步：{} to {}".format(folder.folder_local_path, remote_path))
            shutil.copytree(src=folder.folder_local_path, dst=remote_path, symlinks=True, dirs_exist_ok=True)
        


    def check_process(self):
        """
        检查拷贝进度
        """
        # 查询目标文件夹大小
        folder_info = self.caculate_folder_size(self.remote_root_path)
        size = folder_info[1]
        precent = int(size / self.total_size * 100)
        format_size = self.data_size_format(size)
        print("当前拷贝进度 {}% 目标文件夹大小={}".format(precent, format_size))
        if self.stop_timer == False and precent < 100:
            tiemr = Timer(3, self.check_process)
            tiemr.start()



    def start_timer(self):
        """
        计时器启动
        """
        print("计时器启动")
        self.stop_timer = False        
        t = Timer(0, self.check_process)
        t.start()
    


    def run(self):        
        # 拿到本地的所有文件夹
        local_folders = self.load_folders(carrier.local_root_path)
        self.local_folder_dict = local_folders[0]
        self.total_size = int(local_folders[1])
        # 拿到远端的所有文件夹
        remote_folders = self.load_folders(carrier.remote_root_path)
        self.remote_folder_dict =  remote_folders[0]
        # 拿到所有需要同步的文件夹的名字
        self.folder_list = self.get_changed_list()
        # 如果对比没有差异，本次不需要同步。记录日志。
        if len(self.folder_list) == 0:
            # 写入日志表 
            print("没有需要备份的文件")
            return
        
        # 发送系统通知
        #os.system('osascript -e \'display notification "开始备份..." with title "Carrier" \'')
        
        # 开始进行数据同步  
        self.transfor_data()

    
    
    def clean(self):
        """
        清理已经备份完成的文件夹
        """
        pass
        


if __name__ == '__main__':
    carrier = carrier()
    folder_size = carrier.run()
    

