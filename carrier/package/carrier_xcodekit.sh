#! /bin/zsh


old_ifs=$IFS
IFS=$'\n'

log_file=~/Desktop/carrier_xk.log

function carry_files() {
    local source_path=$1 # ~/Library/Developer/Xcode/UserData/CodeSnippets/
    local des_path=$2 # ~/Library/Developer/Xcode/Templates

    source_last_char="${source_path: -1}"
    if [ "${source_last_char}" != "/" ]; then
      source_path="${source_path}/"
    fi

    des_last_char="${des_path: -1}"
    if [ "${des_last_char}" != "/" ]; then
      des_path="$2/"
    fi

    echo "入参source：$source_path"
    echo "入参des：$des_path"

    # 目标文件夹不存在，先创建
    if ! [ -d "${des_path}" ]; then
      mkdir "${des_path}"
      echo "$(date "+%Y-%m-%d %H:%M:%S"): 创建文件夹 "${des_path}"" >> $log_file
      echo "创建文件夹: ${des_path}"
    fi


    source_list=($(ls "$source_path"))
    echo "source-list: $source_list  文件夹数量=${#source_list[@]}"

    for (( i = 0; i <= ${#source_list[@]}; i++ )); do
        file_name=${source_list[i]}

        source_file="$source_path$file_name"
        echo "本次处理：$source_file"

        if [ -z "$file_name" ]; then
            echo "源文件不存在 $file_name"
            continue
        fi

        # 如果源文件是一个文件
        if [ -f "$source_file" ]; then
            echo "是一个文件：$source_file"
            target_file=$des_path$file_name
            # 目标文件是否存在
            if [ -e "$target_file" ]; then
              # 目标文件和源文件不一致，复制源文件到目标文件
              cmp -s "$target_file" "$source_file"
              if ! [ $? -eq 0 ]; then
                  cp -rf "$source_file" "$target_file"
                  echo "$(date "+%Y-%m-%d %H:%M:%S"): 更新文件 ${target_file}" >> $log_file
                  echo "目标文件需要更新，已复制 ${target_file}"
              else
                  echo "文件不需要更新 ${target_file}"
              fi
            else
                #目标文件不存在
                cp -rf "$source_file" "$target_file"
                echo "$(date "+%Y-%m-%d %H:%M:%S"): 新增文件 ${target_file}" >> $log_file
                echo "目标文件不存在，复制到目标文件夹 ${target_file}"
            fi
        fi

        # 如果是文件夹
        if [ -d "$source_file" ]; then
          target_path=$des_path$file_name
          echo "源文件是一个文件夹，目标位置 ${target_path}"
          carry_files "$source_file" "$target_path"
        fi

    done

}



# 定义变量root_path,存储根目录位置
source_code_snippets_path=~/Library/Developer/Xcode/UserData/CodeSnippets/
target_code_snippets_path=/Users/fengtianyu/Desktop/temp/CodeSnippets/

source_xcode_template_path=~/Library/Developer/Xcode/Templates/
target_xcode_template_path=/Users/fengtianyu/Desktop/temp/XcodeTemplates/

#carry_files $source_code_snippets_path $target_code_snippets_path
carry_files $source_xcode_template_path $target_xcode_template_path


IFS=$old_ifs