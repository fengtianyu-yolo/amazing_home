import os
import shutil
import sqlite3
import time
from threading import Timer
import click
"""
session table 
    session_id - state - progress - start_time - duration - total_size 

log table
    log_id - session_id - file_name - start_time -   
"""

def format_data_size(size) -> str:
    if size > (1024 * 1024 * 1024):  # GB
        result = float(size) / 1024.0 / 1024.0 / 1024.0
        format_result = round(result, 2)
        return "{} GB".format(format_result)
    elif size > (1024 * 1024):  # MB
        result = float(size) / 1024.0 / 1024.0
        format_result = round(result, 2)
        return "{} MB".format(format_result)
    elif size > 1024:  # KB
        result = float(size) / 1024.0
        format_result = round(result, 2)
        return "{} KB".format(format_result)
    else:
        return "{} B".format(size)


class Carrier:

    def __init__(self) -> None:
        self.home_path: str = os.path.expanduser("~")
        self.source_path = os.path.join(self.home_path, "Library/Developer/Xcode/Templates")
        self.destination_path = os.path.join(self.home_path, "Desktop/temp/Template")
        self.db_path = os.path.join(self.home_path, ".carrier.db")
        print(self.source_path)

        self.file_list = []
        self.total_size = 0
        self.finish_size = 0

        self.start_time = int(time.time() * 1000)

        # 连接数据库
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
        self.create_table()

        if not os.path.exists(self.destination_path):
            os.makedirs(self.destination_path)

    def scan(self, sub_path=""):

        current_root_path = os.path.join(self.source_path, sub_path)

        # 遍历当前路径下所有文件夹
        for item in os.listdir(current_root_path):

            # 拿到文件路径
            current_file = os.path.join(current_root_path, item)

            # 如果是一个文件夹
            if os.path.isdir(current_file):
                # 目标位置文件夹路径
                target_path = os.path.join(self.destination_path, sub_path, item)

                # 目标位置不存在该文件夹，创建文件夹
                if not os.path.exists(target_path):
                    os.mkdir(target_path)

                # 拼接相对路径  如 Template/iOS
                full_sub_path = os.path.join(sub_path, item)
                self.scan(full_sub_path)

            # 如果源文件是一个文件
            elif os.path.isfile(current_file):

                # 构造目标文件路径
                target_file = os.path.join(self.destination_path, sub_path, item)
                # print("源文件={}, 目标文件={}".format(current_file, target_file))

                # 如果目标文件不存在：将该源文件路径和目标文件路径添加到容器
                if not os.path.exists(target_file):
                    item = (current_file, target_file, "new")
                    self.file_list.append(item)
                    # 统计总共的文件大小
                    source_file_stat = os.stat(current_file)
                    self.total_size += source_file_stat.st_size
                else:
                    # 如果文件存在，拿到源文件和目标文件的元数据
                    source_file_stat = os.stat(current_file)
                    target_file_stat = os.stat(target_file)

                    if source_file_stat.st_size != target_file_stat.st_size:
                        file_tuple = (current_file, target_file, "update")
                        self.file_list.append(file_tuple)
                        self.total_size += source_file_stat.st_size
                    elif source_file_stat.st_mtime != target_file_stat.st_mtime:
                        file_tuple = (current_file, target_file, "update")
                        self.file_list.append(file_tuple)
                        self.total_size += source_file_stat.st_size
            else:
                print("未知数据 {}".format(current_file))

    def move(self):

        if len(self.file_list) == 0:
            self.insert_session(1, 100)
            return

        # 写入日志
        self.insert_session(0, 0)

        for item in self.file_list:
            source = item[0]
            des = item[1]
            shutil.copy2(source, des)
            file_info = os.stat(des)
            self.finish_size += file_info.st_size

            # 更新数据库的进度
            progress = int(self.finish_size / self.total_size * 100)
            self.update_session(progress)

    def start_progress_observer(self):
        # 没有要拷贝的文件，不需要启动计时器
        if len(self.file_list) == 0:
            return

        if self.total_size <= 0:
            tiemr = Timer(1, self.start_progress_observer)
            tiemr.start()
        else:
            progress = self.finish_size / self.total_size
            if progress >= 1.0:
                return
            else:
                tiemr = Timer(1, self.start_progress_observer)
                tiemr.start()

    def create_table(self):
        create_session_table = """
        create table if not exists session_table(
            session_id integer primary key autoincrement,
            state integer,
            progress integer default 0,
            start_time integer,
            duration integer,
            total_size integer default 0
        )
        """
        self.cursor.execute(create_session_table)
        create_info_table = """
            create table if not exists info_table(
                id integer primary key autoincrement, 
                file_name text,
                start_time time,
                session_id integer 
            )
        """
        self.cursor.execute(create_info_table)

    def insert_session(self, session_state, session_progress):

        session_log = """
            insert into session_table ('state', 'progress', 'start_time', 'duration', 'total_size') values(
                {state},
                {progress},
                {start_time},
                0,
                {total_size}
            )
        """.format(state=session_state, progress= session_progress, start_time=self.start_time, total_size=self.total_size)
        self.cursor.execute(session_log)
        self.connection.commit()
        pass

    def update_session(self, session_progress):
        session_state = 1 if session_progress >= 100 else 0
        current_time = int(time.time() * 1000)
        session_duration = current_time - self.start_time

        update_session_sql = """
            update session_table 
            set progress = {progress}, state = {state}, duration = {duration}
            from (select * from session_table order_by start_time desc limit 1) as t2 where session_table.session_id = t2.id 
        """.format(progress=session_progress, state=session_state, duration=session_duration, session_id=1)
        self.cursor.execute(update_session_sql)
        self.connection.commit()


if __name__ == '__main__':
    carrier = Carrier()
    carrier.scan()
    carrier.move()

