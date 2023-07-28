#! /bin/zsh

# 定义变量root_path,存储根目录位置
root_path="/Users/fengtianyu/Downloads"

# 把文件夹下的文件放到数组 folder_list = [[name, size, count], [name, size, count]]
folder_name_list=($(ls $root_path))
# 定义一个数组
declare -a folder_list

# 遍历文件夹名字
for ((i=0; i<${#folder_name_list[@]}; i++)) do
    # 定义一个字典
    declare -A dict 
    # 把文件夹名字放到字典
    #echo $folder_name_list[i]
    dict["name"]=$folder_name_list[i]
    dict["size"]=12
    # 把字典放到数组
    declare -i index=$i+1
    folder_list[index]=${dict}
done

#echo ${folder_list[@]}

for dict in ${folder_list[@]}
do    
    # echo ${!dict[*]}
done

#for folder in ${folder_name_list[@]}
#do
#    echo $folder
#done

#echo ${folder_list}


#for file_item in $(ls $root_path)
#do
#    echo $file_item
#done

