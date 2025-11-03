#!/usr/bin/env python3
"""
JavSP GUI启动脚本
直接启动图形用户界面
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_tkinter():
    """检查tkinter是否可用"""
    try:
        import tkinter
        return True
    except ImportError:
        return False

def main():
    """主函数"""
    print("JavSP GUI启动器")
    print("=" * 50)

    # 检查tkinter
    if not check_tkinter():
        print("✗ 错误: 未找到tkinter模块")
        print("请安装tkinter:")
        print("  Ubuntu/Debian: sudo apt-get install python3-tk")
        print("  CentOS/RHEL: sudo yum install tkinter")
        print("  Windows: tkinter通常已包含在Python中")
        print("  macOS: tkinter通常已包含在Python中")
        return False

    print("✓ tkinter支持正常")

    try:
        # 临时启用GUI模式
        import tempfile
        import yaml

        # 创建临时配置文件
        config_content = """
general:
  enable_gui: true
  enable_incremental_scan: true
  cache_file: "data/scan_cache.json"
  cache_cleanup_interval: 30

scanner:
  input_directory: null
  filename_extensions: [.mp4, .avi, .mkv, .mov, .wmv, .flv, .m4v, .3gp, .rmvb, .rm, .ts, .vob, .iso, .m2ts, .strm, .mpg]
  ignored_folder_name_pattern: ['^\\.', '^#recycle$', '^#整理完成$', '^#不要扫描$']
  minimum_size: 50MiB
  skip_nfo_dir: true
  manual: false
  ignored_id_pattern: ['(144|240|360|480|720|1080)[Pp]', '[24][Kk]', '\\w+2048\\.com', 'Carib(beancom)?', '[^a-z\\d](f?hd|lt)[^a-z\\d]']

network:
  proxy_server: null
  retry: 3
  timeout: PT30S
  proxy_free:
    airav: null
    avsox: null
    avwiki: null
    dl_getchu: null
    fanza: null
    fc2: null
    fc2fan: null
    fc2ppvdb: null
    gyutto: null
    jav321: null
    javbus: null
    javdb: null
    javlib: null
    javmenu: null
    mgstage: null
    njav: null
    prestige: null
    arzon: null
    arzon_iv: null

crawler:
  selection:
    normal: [javdb, javlib, avsox, javbus, fanza, mgstage, dmm, airav, fc2fan, fc2ppvdb, gyutto, dl_getchu, arzon, arzon_iv, njav]
    fc2: [fc2fan, fc2ppvdb, javdb, javlib, avsox, javbus, airav, njav]
    cid: [mgstage, javdb, javlib, avsox, javbus, fanza, airav, fc2fan, fc2ppvdb, njav]
    getchu: [dl_getchu, javdb, javlib, avsox, javbus, fanza, airav]
    gyutto: [gyutto, javdb, javlib, avsox, javbus, fanza, airav]
  priority:
    normal: [avsox, javdb, fanza, mgstage, javlib, javbus, airav, fc2fan, fc2ppvdb, dmm, njav, gyutto, dl_getchu, arzon, arzon_iv]
    fc2: [fc2fan, fc2ppvdb, njav, javdb, javlib, avsox, javbus, airav]
    cid: [mgstage, javdb, avsox, javlib, javbus, fanza, airav, fc2fan, fc2ppvdb, njav]
    getchu: [dl_getchu, javdb, avsox, javlib, javbus, fanza, airav]
    gyutto: [gyutto, javdb, avsox, javlib, javbus, fanza, airav]
  enable_cloudscraper: true
  ignore_404: false
  max_concurrent_requests: 5
  normalize_actress_name: true
  max_actress_count: 10
  use_javdb_cover: fallback

summarizer:
  default:
    title: "未知标题"
    actress: "未知演员"
    publish_date: "1970-01-01"
    duration: "0"
    plot: "暂无剧情简介"
  censor_options_representation: ["有码", "无码", "有码", "有码"]
  title:
    remove_trailing_actor_name: true
  operation_mode: scrape_and_organize
  move_files: true
  path:
    output_dir: "output"
    basename_pattern: "{title}-{dvdid}"
    length_maximum: 100
    length_by_byte: false
    max_actress_count: 10
    move_mode: move
    link_failure_strategy: hard_link
    use_absolute_paths: true
  nfo:
    basename_pattern: "movie"
    title_pattern: "{title}"
    custom_genres_fields: ["genre_norm"]
    custom_tags_fields: []
  cover:
    basename_pattern: "poster"
    highres: false
    add_label: false
    crop:
      engine: null
      on_id_pattern: []
  fanart:
    basename_pattern: "fanart"
  extra_fanarts:
    enabled: true
    scrap_interval: PT1.5S

translator:
  engine: null
  fields:
    title: true
    plot: true

other:
  interactive: true
  check_update: true
  auto_update: false
"""

        # 启动GUI
        print("✓ 启动GUI界面...")

        # 临时设置环境变量以启用GUI
        os.environ['JAVSP_GENERAL_ENABLE_GUI'] = 'true'

        # 直接导入并运行GUI
        from javsp.gui.app import JavSPApp

        app = JavSPApp()
        app.run()

        return True

    except ImportError as e:
        print(f"✗ 导入错误: {e}")
        print("请确保已安装所需依赖:")
        print("  pip install pydantic confz requests colorama tqdm Pillow")
        return False

    except Exception as e:
        print(f"✗ 启动失败: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"未处理的错误: {e}")
        sys.exit(1)