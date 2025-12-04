import os
from ultralytics import YOLO
from typing import List, Dict, Any, Tuple

# モデルファイルが存在するディレクトリへの相対パスを設定
# services/ から見て '../yolov8_DataSet/' にアクセス
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'yolov8_DataSet')

# 読み込むモデルファイル名と、それに紐づく検出カテゴリ
MODEL_PATHS = [
    # モデルファイル名: category (このカテゴリ名が最終的な検出結果に使われる)
    ("tomato_best.pt", "disease"),
    ("pest_best.pt", "pest")
]

# モデルロード時に使用するリスト (サーバー起動時にメモリにロード)
yolo_model_list: List[Tuple[YOLO, str]] = []

# --- サーバー起動時に一度だけ実行される初期化処理 ---
def load_models():
    """MODEL_PATHSに指定されたすべてのYOLOv8モデルをロードする"""
    print("--- YOLOv8モデルの初期化中 ---")
    
    # グローバルリストをクリア（念のため）
    yolo_model_list.clear() 

    for model_name, category in MODEL_PATHS:
        full_path = os.path.join(MODEL_DIR, model_name)
        
        if not os.path.exists(full_path):
            print(f"❌ モデルファイルが見つかりません: {full_path}")
            # モデルが見つからない場合は、推論時にエラーを発生させるため、ロードはスキップ
            continue

        try:
            # YOLOモデルをロード
            model = YOLO(full_path)
            yolo_model_list.append((model, category))
            print(f"✅ モデルロード成功: {model_name} (カテゴリ: {category})")
        except Exception as e:
            print(f"❌ モデルのロード中にエラーが発生しました ({model_name}): {e}")
            
    if not yolo_model_list:
        # 少なくとも1つモデルがないと推論できないため、エラーとして扱う
        raise ConnectionError("AIモデルのロードに失敗しました。ファイルパスとファイル名を確認してください。")

# サーバー起動時にこの関数を呼び出す必要があるため、外部から呼び出せるようにしておく
# NOTE: 適切なタイミングで routes.py や app.py から load_models() を呼び出す必要があります。

# --- 推論実行ロジック ---
def run_detection_and_analyze(image_path: str) -> Tuple[str, float, List[Dict[str, Any]]]:
    """
    ロード済みのすべてのモデルで推論を実行し、結果を統合・分析して返す。
    routes.py が期待する3つの値を返すように修正。
    """
    if not yolo_model_list:
        raise ConnectionError("YOLOv8モデルがロードされていません。")

    all_detections = []
    
    # --- 1. すべてのモデルで推論を実行し、all_detectionsに結果を統合 ---
    for model, category in yolo_model_list:
            # モデルごとの推論を実行
            results = model(image_path)
            
            # 結果の解析
            if results and results[0].boxes:
                r = results[0]
                
                for box in r.boxes:
                    class_id = int(box.cls.item())
                    confidence = round(box.conf.item(), 3)
                    # モデルのクラス名（例: Early blight）にカテゴリ（disease/pest）を付与
                    class_name = model.names[class_id] 
                    
                    # バウンディングボックス座標 (xyxy) を整数に変換
                    x_min, y_min, x_max, y_max = [int(x) for x in box.xyxy[0].tolist()]

                    # 結果を統合リストに追加
                    all_detections.append({
                        "disease": f"{class_name} ({category})", # どのモデルの何のクラスか分かるようにカテゴリを付与
                        "confidence": confidence,
                        "model_category": category, 
                        "box": {
                            "x_min": x_min, "y_min": y_min, "x_max": x_max, "y_max": y_max
                        }
                    })
    # --- 2. 結果の集約と整形 (以前の get_best_detection のロジック) ---
    if not all_detections:
        # 検出がなかった場合
        return "健康 (検出なし)", 1.0, []
    
    # 最も確信度の高い検出結果を特定
    best_detection = max(all_detections, key=lambda d: d['confidence'])
    
    final_disease = best_detection['disease']
    final_confidence = best_detection['confidence']
    
    # --- 3. 3つの値を返す ---
    return final_disease, final_confidence, all_detections # ★ 3つの値を返すように修正 ★

# --- 結果の集約と整形ロジック ---
def get_best_detection(detections: List[Dict[str, Any]]) -> Tuple[str, float, List[Dict[str, Any]]]:
    """
    検出結果リストから、最も確信度の高い結果を抽出する。
    """
    if not detections:
        return "健康 (検出なし)", 1.0, []
    
    # 最も確信度の高い検出結果を特定
    best_detection = max(detections, key=lambda d: d['confidence'])
    
    final_disease = best_detection['disease']
    final_confidence = best_detection['confidence']
    
    return final_disease, final_confidence, detections
