"""
数据处理管线包装器 — 调用 data_process/ 中的算法
支持：
1. CSV 文件上传替换
2. 触发完整预处理 + 风险划分 + 分区域分析管线
3. 清除缓存并重新加载数据
"""
import os, sys, subprocess, shutil
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PROCESS_DIR = os.path.join(BASE_DIR, "data_process", "代码")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_uploaded_csv(file_content: bytes, filename: str) -> str:
    """保存上传的 CSV 文件，返回保存路径"""
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(file_content)
    return filepath


def validate_csv(filepath: str) -> dict:
    """验证 CSV 文件是否可用于系统"""
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig')
    except Exception:
        try:
            df = pd.read_csv(filepath, encoding='gbk')
        except Exception as e:
            return {"valid": False, "error": f"无法读取CSV: {str(e)}"}

    required_cols = ["果树品种", "病虫害类型"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return {
            "valid": False,
            "error": f"缺少必要列: {', '.join(missing)}",
            "columns": list(df.columns),
            "rows": len(df),
        }

    return {
        "valid": True,
        "columns": list(df.columns),
        "rows": len(df),
        "varieties": df["果树品种"].unique().tolist() if "果树品种" in df.columns else [],
    }


def run_preprocessing(input_path: str) -> dict:
    """运行预处理管线（数据挖掘 + 预处理）"""
    results = {"success": True, "steps": []}

    # Step 1: 数据挖掘
    step1 = os.path.join(PROCESS_DIR, "1.预处理", "数据挖掘.py")
    if os.path.exists(step1):
        try:
            subprocess.run(
                ["python", step1],
                cwd=BASE_DIR,
                timeout=300,
                capture_output=True,
                text=True,
            )
            results["steps"].append("数据挖掘完成")
        except subprocess.TimeoutExpired:
            results["steps"].append("数据挖掘超时（跳过）")
        except Exception as e:
            results["steps"].append(f"数据挖掘失败: {str(e)}")

    # Step 2: 预处理
    step2 = os.path.join(PROCESS_DIR, "1.预处理", "预处理.py")
    if os.path.exists(step2):
        try:
            subprocess.run(
                ["python", step2],
                cwd=BASE_DIR,
                timeout=300,
                capture_output=True,
                text=True,
            )
            results["steps"].append("预处理完成")
        except subprocess.TimeoutExpired:
            results["steps"].append("预处理超时（跳过）")
        except Exception as e:
            results["steps"].append(f"预处理失败: {str(e)}")

    return results


def run_risk_modeling() -> dict:
    """运行风险划分管线（LightGBM 训练 + SHAP）"""
    results = {"success": True, "steps": []}

    step = os.path.join(PROCESS_DIR, "2.风险划分", "风险划分.py")
    if os.path.exists(step):
        try:
            subprocess.run(
                ["python", step],
                cwd=BASE_DIR,
                timeout=600,
                capture_output=True,
                text=True,
            )
            results["steps"].append("风险模型训练完成")
        except subprocess.TimeoutExpired:
            results["steps"].append("模型训练超时（跳过）")
        except Exception as e:
            results["steps"].append(f"模型训练失败: {str(e)}")

    return results


def run_spatial_analysis() -> dict:
    """运行分区域分时段分析"""
    results = {"success": True, "steps": []}

    step = os.path.join(PROCESS_DIR, "分区域、分时段", "精准防控分析.py")
    if os.path.exists(step):
        try:
            subprocess.run(
                ["python", step],
                cwd=BASE_DIR,
                timeout=600,
                capture_output=True,
                text=True,
            )
            results["steps"].append("精准防控分析完成")
        except subprocess.TimeoutExpired:
            results["steps"].append("精准防控分析超时（跳过）")
        except Exception as e:
            results["steps"].append(f"精准防控分析失败: {str(e)}")

    return results


def run_full_pipeline(input_path: str) -> dict:
    """运行完整数据处理管线"""
    results = {
        "success": True,
        "input": input_path,
        "steps": [],
        "warnings": [],
    }

    # 仅在本地环境运行（Vercel serverless 不支持 subprocess 长时间任务）
    if os.environ.get("VERCEL"):
        results["steps"].append("Vercel 环境，跳过算法管线")
        results["warnings"].append("算法管线需在本地运行。上传的 CSV 将用于直接展示。")
        return results

    results["steps"].append("开始完整管线...")

    # Step 1: 预处理
    pre_results = run_preprocessing(input_path)
    results["steps"].extend(pre_results.get("steps", []))

    # Step 2: 风险划分
    risk_results = run_risk_modeling()
    results["steps"].extend(risk_results.get("steps", []))

    # Step 3: 分区域分析
    spatial_results = run_spatial_analysis()
    results["steps"].extend(spatial_results.get("steps", []))

    results["steps"].append("管线执行完毕")
    return results
