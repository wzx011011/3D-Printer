import subprocess
from pathlib import Path

from pathlib import Path
import shutil
def process_sym_files():
    try:
        # 执行 dump_syms 命令
        subprocess.run([
			r'C:\breakpad\breakpad\dump_syms.exe', 
			r'CrealityPrint_Slicer.pdb', 
			'>', 
			'CrealityPrint_Slicer.sym'
		], shell=True)

        # 验证文件生成
        sym_file = Path('CrealityPrint_Slicer.sym')
        if not sym_file.exists():
            raise FileNotFoundError("符号文件未成功生成")

        # 读取第一行（自动处理编码）
        with sym_file.open('r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('MODULE'):
                parts = first_line.strip().split()
                if len(parts) >=5 :
                    info =  {
                        "os": parts[1],
                        "arch": parts[2],
                        "module_id": parts[3],
                        "pdb_name": parts[4]
                    }
                    f.close()
                    target_dir = Path("symbols") / Path(info["pdb_name"]) / info["module_id"]
                    target_dir.mkdir(parents=True, exist_ok=True)
                    src = Path("CrealityPrint_Slicer.sym")
                    shutil.move(str(src), str(target_dir / src.name))
                    print("execute ok")
                    
            print(f"首行内容：{first_line}")

    except subprocess.CalledProcessError as e:
        print(f"命令执行失败：{e.stderr.decode()}")
    except Exception as e:
        print(f"错误发生：{str(e)}")

if __name__ == "__main__":
    process_sym_files()
    print("finish")
