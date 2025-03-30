import os
import sys
import shutil
from typing import List, Optional, Union, Dict, Tuple
from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont

from loguru import logger

logger.remove()
logger.add(
    sys.stderr,
    format="[{time:HH:mm:ss}] [{level:4}] {message}",
    level="DEBUG",
    colorize=True
)

FONT_TYPE_REGULAR = "Regular"
FONT_TYPE_BOLD = "Bold"
FONT_TYPE_LIGHT = "Light"

SYSTEM_FONT_FILES: Dict[str, Tuple[str, bool]] = {
    "msyh": (r"C:\Windows\Fonts\msyh.ttc", FONT_TYPE_REGULAR, False),
    "msyhbd": (r"C:\Windows\Fonts\msyhbd.ttc", FONT_TYPE_BOLD, False),
    "msyhl": (r"C:\Windows\Fonts\msyhl.ttc", FONT_TYPE_LIGHT, False),
    "simsun": (r"C:\Windows\Fonts\simsun.ttc", FONT_TYPE_REGULAR, False),
    "simsunb": (r"C:\Windows\Fonts\simsunb.ttf", FONT_TYPE_REGULAR, True)
}

BACKUP_DIR = "Backup"
CONVERTED_OLD_DIR = "Converted/Old"
CONVERTED_NEW_DIR = "Converted/New"
OUTPUT_DIR = "Output"
INPUT_DIR = "Input"

def ensure_dir(dir_path: str) -> None:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

def backup_fonts() -> bool:
    try:
        ensure_dir(BACKUP_DIR)

        for font_name, (font_path, _, _) in SYSTEM_FONT_FILES.items():
            if os.path.exists(font_path):
                file_name = os.path.basename(font_path)
                dest_path = os.path.join(BACKUP_DIR, file_name)
                shutil.copy2(font_path, dest_path)
                logger.success(f'已复制 {font_path} -> {dest_path}')
            else:
                logger.error(f'文件不存在 {font_path}')
                
        return True
    except Exception as e:
        logger.error(f'{e}')
        return False

def unpack_ttc(input_path: str, output_dir: str) -> Optional[List[str]]:
    try:
        input_path = Path(input_path)
        if not input_path.exists():
            logger.error(f'文件不存在 {input_path}')
            return None

        ensure_dir(output_dir)

        try:
            ttc_collection = TTCollection(input_path)
            num_fonts = len(ttc_collection.fonts)
        except Exception as e:
            logger.error(f'无法打开 TTC 文件 {e}')
            if "Not a TTC file" in str(e):
                 logger.info(f'不是有效的 TTC 文件 {input_path}')
                 return None
            else:
                 return None

        logger.info(f'开始解包 {input_path}')
        logger.info(f'这个 TTC 包含 {num_fonts} 个字体')

        output_files = []

        for i in range(num_fonts):
            logger.info(f'正在处理第 {i + 1} / {num_fonts} 个')
            try:
                font = ttc_collection.fonts[i]

                font_name = f"font_{i}"
                for name in font['name'].names:
                    if name.nameID == 1 and not name.isUnicode():
                        try:
                            font_name = name.string.decode('latin-1')
                        except UnicodeDecodeError:
                            try:
                                font_name = name.string.decode('utf-16be') # Try another common encoding
                            except Exception as decode_err:
                                logger.warning(f"无法解码字体名称 record {name.nameID} ({name.platformID}, {name.platEncID}, {name.langID}) {decode_err}")
                                font_name = f"font_{i}_decode_error"
                        break

                output_path = os.path.join(
                    output_dir,
                    f"{input_path.stem}_{font_name}.ttf"
                )

                font.save(output_path)
                output_files.append(output_path)
                logger.success(f"已保存 {output_path}")

            except Exception as e:
                logger.error(f'解包失败 {e}')
                continue

        logger.info(f'解包完成')
        return output_files

    except Exception as e:
        logger.error(f'解包失败 {e}')
        return None

def _copy_font_attributes(source_font: TTFont, target_font: TTFont) -> None:
    if 'name' in source_font and 'name' in target_font:
        target_font['name'].names = [
            rec for rec in target_font['name'].names
            if rec.nameID not in [0, 1, 2, 3, 4, 5, 6, 8, 9]
        ]
        for name_record in source_font['name'].names:
            if name_record.nameID in [0, 1, 2, 3, 4, 5, 6, 8, 9]:
                target_font['name'].names.append(name_record)
        target_font['name'].names.sort(key=lambda rec: (rec.platformID, rec.platEncID, rec.langID, rec.nameID))

    if 'OS/2' in source_font and 'OS/2' in target_font:
        for attr in ['usWeightClass', 'usWidthClass', 'fsSelection']:
            if hasattr(source_font['OS/2'], attr):
                setattr(target_font['OS/2'], attr, getattr(source_font['OS/2'], attr))

    if 'head' in source_font and 'head' in target_font:
        if hasattr(source_font['head'], 'macStyle'):
            target_font['head'].macStyle = source_font['head'].macStyle

    if 'post' in source_font and 'post' in target_font:
        for attr in ['italicAngle', 'underlinePosition', 'underlineThickness', 'isFixedPitch']:
            if hasattr(source_font['post'], attr):
                setattr(target_font['post'], attr, getattr(source_font['post'], attr))

def copy_and_apply_font_attributes(source_file_or_dir: str, target_file: str, output_dir: str, single_file: bool = False) -> Optional[bool]:
    try:
        target_file_path = Path(target_file)
        if not target_file_path.exists():
            logger.error(f'目标文件不存在 {target_file}')
            return False if single_file else None

        ensure_dir(output_dir)

        if single_file:
            source_file_path = Path(source_file_or_dir)
            if not source_file_path.exists():
                logger.error(f'源文件不存在 {source_file_or_dir}')
                return False

            output_file = os.path.join(output_dir, f"{source_file_path.stem}.ttf")
            ensure_dir(os.path.dirname(output_file))

            shutil.copy2(target_file, output_file)

            source_font = TTFont(source_file_or_dir)
            target_font = TTFont(output_file, recalcBBoxes=False, recalcTimestamp=False)

            _copy_font_attributes(source_font, target_font)

            target_font.save(output_file)
            logger.info(f'已拷贝属性 {os.path.basename(source_file_or_dir)} -> {os.path.basename(output_file)}')
            return True

        else:
            # 批量处理逻辑
            source_dir = Path(source_file_or_dir)
            if not source_dir.exists():
                logger.error(f'输入路径不存在 {source_file_or_dir}')
                return None

            source_files = list(source_dir.glob("*.ttf"))

            if not source_files:
                logger.warning(f'输入路径中没有 TTF 文件 {source_file_or_dir}')
                return None

            for i, source_path in enumerate(source_files):
                output_filename = f"{target_file_path.stem}{i + 1}.ttf"
                output_path = os.path.join(output_dir, output_filename)

                try:
                    shutil.copy2(target_file, output_path)

                    source_font = TTFont(source_path)
                    target_font = TTFont(output_path, recalcBBoxes=False, recalcTimestamp=False)

                    # 修改字体属性
                    _copy_font_attributes(source_font, target_font)

                    target_font.save(output_path)
                    logger.info(f'已拷贝属性 {source_path.name} -> {output_filename}')

                except Exception as e:
                    logger.error(f'处理失败 {source_path.name} -> {output_filename} {e}')

            return True

    except Exception as e:
        logger.error(f'处理失败 {e}')
        return False if single_file else None

def pack_ttc(input_dir: str, output_dir: str) -> None:
    try:
        if not input_dir or not output_dir:
            logger.error("输入或输出目录为空")
            return

        input_dir_path = Path(input_dir)
        if not input_dir_path.exists():
            logger.error(f'目录不存在 {input_dir}')
            return

        ensure_dir(output_dir)

        ttf_files = list(input_dir_path.glob("*.ttf"))
        ttf_files.sort()

        if not ttf_files:
            logger.warning(f'没有 TTF 文件 {input_dir}')
            return

        logger.debug(f"被打包的 TTF 文件 {', '.join(str(f) for f in ttf_files)}")

        fonts = []
        for ttf_file in ttf_files:
            try:
                logger.debug(f"加载 TTF 文件 {ttf_file}")
                font = TTFont(ttf_file)
                fonts.append(font)
            except Exception as e:
                logger.error(f'加载 TTF 文件失败 {ttf_file} {e}')

        if not fonts:
            logger.error(f'没有可用的 TTF 文件 {input_dir}')
            return

        output_filename = f"{input_dir_path.name}.ttc"
        output_path = os.path.join(output_dir, output_filename)

        ttc = TTCollection()
        ttc.fonts = fonts
        ttc.save(output_path)
        logger.info(f'已打包 {input_dir} -> {output_path}')

    except Exception as e:
        logger.error(f'打包失败 {e}')

def process_font(font_name: str, input_file: str, single_file: bool = False) -> None:
    backup_path = os.path.join(BACKUP_DIR, f"{font_name}.ttc" if not single_file else f"{font_name}.ttf")
    old_dir = os.path.join(CONVERTED_OLD_DIR, font_name)
    new_dir = os.path.join(CONVERTED_NEW_DIR, font_name)
    
    if not single_file:
        unpack_ttc(backup_path, old_dir)
        copy_and_apply_font_attributes(old_dir, input_file, new_dir)
        pack_ttc(new_dir, OUTPUT_DIR)
    else:
        copy_and_apply_font_attributes(backup_path, input_file, new_dir, single_file=True)
        output_file = os.path.join(OUTPUT_DIR, f"{font_name}.ttf")
        shutil.copy2(os.path.join(new_dir, f"{font_name}.ttf"), output_file)

if __name__ == '__main__':
    if not backup_fonts():
        if input(f'\n备份过程中可能有错误发生。您想要继续吗 (y/N)').lower() != 'y':
            sys.exit(2)
    
    for directory in [BACKUP_DIR, CONVERTED_OLD_DIR, CONVERTED_NEW_DIR, OUTPUT_DIR]:
        ensure_dir(directory)
    
    for font_name, (_, font_type, is_single_file) in SYSTEM_FONT_FILES.items():
        input_file = os.path.join(INPUT_DIR, f"{font_type}.ttf")
        process_font(font_name, input_file, is_single_file)

    logger.info("操作成功完成")