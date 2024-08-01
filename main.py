# osu2PJDL
# Author:Suichen
import string
import zipfile
import os
import json
import shutil
import random
import math


def osz_unzip(osz: str) -> str:
    # 解决解压缩后乱码问题
    zip = zipfile.ZipFile(osz, metadata_encoding='UTF-8')
    os.mkdir(osz.split('.')[0])
    zip.extractall(osz.split('.')[0])
    zip.close()
    return osz.split('.')[0]


def gen_random_uid(length: int = 13) -> str:
    uid_random_str_list = list(string.ascii_lowercase) + list(string.digits)
    random_uid = ''
    for i in range(length):
        random_uid += uid_random_str_list[random.randint(0, len(uid_random_str_list) - 1)]
    return random_uid


def osu2json(file_path: str, file_dir: str) -> str:
    global sound_path, corrected, bg
    if not file_dir.endswith('\\'):
        file_dir += '\\'
    print('osz_path:', file_dir)
    with open(file_path, 'r', encoding='UTF-8-sig') as f:
        chart = f.read().split("\n")

    last_para = ""
    dict_chart = dict()
    for i in chart:
        # 新分节判定
        if i.startswith('[') and i.endswith(']'):
            last_para = i[1:-1]
        else:
            # 非空判断
            if i != "" and last_para != '':
                # 列表或键值对判断
                key_pair = i.split(': ')
                if len(key_pair) == 1:
                    # 列表
                    key_list = i.split(',')
                    combined_list = list()
                    for j in key_list:
                        combined_list.append(j)
                    if dict_chart.get(last_para, None) is None:
                        dict_chart[last_para] = list()
                    dict_chart[last_para].append(combined_list)
                else:
                    if dict_chart.get(last_para, None) is None:
                        dict_chart[last_para] = dict()
                    dict_chart[last_para][key_pair[0]] = key_pair[1]

    # 谱面解析 Part 2
    # 提取必要信息
    # 因存储格式，导致数字以及其他类型数据均为文本
    if dict_chart['General']['Mode'] != "3" and dict_chart['Difficulty']['CircleSize'] != "4":
        return '非osu! mania 4k谱面'
    # 谱面信息提取
    song = dict_chart['General']['AudioFilename']
    song_name = dict_chart['Metadata']['TitleUnicode']
    creator = dict_chart['Metadata']['Creator']
    info = f'曲师：{dict_chart['Metadata']['ArtistUnicode']}\n{dict_chart['Metadata']['Version']}'
    for i in dict_chart['Events']:
        if len(i) == 5 and i[0] == "0" and i[1] == "0":
            bg = i[2][1:-1]
            break
    beat_length = -1
    start_time = 0
    for i in dict_chart['TimingPoints']:
        if i[6] == "1":
            if beat_length != -1:
                return "不支持变速谱"
            beat_length = float(i[1])
            start_time = int(i[0])
    print(song_name, creator, info, beat_length, start_time)
    bpm = 1 / beat_length * 1000 * 60
    bpm = round(bpm, 3)
    corrected = start_time / 1000
    # 谱面解析 Part 3
    beat_length_offset = round(beat_length - beat_length, 3)
    notes = list()
    for i in dict_chart['HitObjects']:
        key = math.floor(int(i[0]) * 4 / 512)
        note_time_start = int(i[2]) - start_time
        beat = note_time_start // beat_length
        counting_offset = (beat_length_offset * beat) % (beat_length // 48)
        beat_i = round((note_time_start % beat_length) / beat_length * 48) - round(counting_offset)
        if beat_i == 48:
            beat += 1
            beat_i = 0
        # 出现了令人难绷节拍偏移问题
        # 本来为了方便计算，将一拍时间简化为整数，可这会导致偏移，所以换回小数了
        beat = int(beat)
        if i[3] == "128":
            note_time_end = int(i[5].split(':')[0]) - start_time
            drag = round((note_time_end - note_time_start) / beat_length * 48) - round(counting_offset)
            notes.append([beat, beat_i, drag, key])
            print([beat, beat_i, drag, key])
        else:
            notes.append([beat, beat_i, 0, key])
            print([beat, beat_i, 0, key])

    os.makedirs(f'export/{song_name}', exist_ok=True)
    if not os.path.exists(f'export/{song_name}'):
        path_name = gen_random_uid()
    else:
        path_name = song_name
    if os.path.exists(f'export/{path_name}'):
        shutil.rmtree(f'export/{path_name}')
    if os.path.exists(f'export/{path_name}.pjdlc'):
        os.remove(f'export/{path_name}.pjdlc')
    os.makedirs(f'export/{path_name}')

    shutil.copy(f'{file_dir}{song}', f'export/{path_name}/song.ogg')
    shutil.copy(f'{file_dir}{bg}', f'export/{path_name}/cover.jpg')
    shutil.rmtree(file_dir)

    # 构造json
    final_dict = dict()
    final_dict['author'] = creator
    final_dict['bpm'] = bpm
    final_dict['corrected'] = corrected
    final_dict['info'] = info
    final_dict['name'] = song_name
    final_dict['notes'] = notes
    final_dict['tags'] = []

    with open(f'export/{path_name}/chart.json', 'w', encoding='UTF-8') as chart:
        json.dump(final_dict, chart, ensure_ascii=False, indent=None)
    with open(f'export/{path_name}.pjdlc', 'wb+') as fo:
        with zipfile.ZipFile(file=fo, mode="w") as pjdlc:
            pjdlc.write(f'export/{path_name}/song.ogg', arcname='song.ogg')
            pjdlc.write(f'export/{path_name}/cover.jpg', arcname='cover.jpg')
            pjdlc.write(f'export/{path_name}/chart.json', arcname='chart.json')
    shutil.rmtree(f'export/{path_name}')
    return f'操作完成，请查看 export/{path_name}.pjdlc'


if __name__ == '__main__':

    osz_path = input('请输入py文件目录下osz名：')
    osz_name = osz_path.split('.')[0]
    if os.path.exists(osz_name):
        shutil.rmtree(osz_name)
    osz_unzip(osz_path)
    osu_files = list()
    for root, dirs, files in os.walk(osz_name):
        for file in files:
            # 构建相对路径
            relative_path = os.path.relpath(os.path.join(root, file), osz_name)
            if relative_path.endswith('.osu'):
                osu_files.append(relative_path)
    for i in range(len(osu_files)):
        print(f'{i}:{osu_files[i]}')

    nums = input('请输入欲转换osu文件名序号：')
    osu_path = ''
    osu_file = os.path.relpath(os.path.join(osz_name, osu_files[int(nums)]))
    for i in osu_file.split("\\")[:-1]:
        osu_path += i + '\\'
    osu_path = os.path.relpath(osu_path)
    print(osu2json(osu_file, osu_path))
