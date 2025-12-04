import os
from ultralytics import YOLO
from typing import List, Dict, Any, Tuple
import cv2 # 画像描画のために追加
import uuid # ユニークなファイル名生成のために追加

# モデルファイルが存在するディレクトリへの相対パスを設定
# services/ から見て '../yolov8_DataSet/' にアクセス
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'yolov8_DataSet')

# 推論直後の一時保存フォルダ (project_c_minimum/temp_inference_results) を削除
# TEMP_INFERENCE_RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp_inference_results')
# os.makedirs(TEMP_INFERENCE_RESULTS_DIR, exist_ok=True)

# 読み込むモデルファイル名と、それに紐づく検出カテゴリ
# MODEL_PATHS = [
#     ("tomato_best.pt", "disease"),
#     ("pest_best.pt", "pest")
# ] # この行は削除またはコメントアウト

# MODEL_DIR内の.ptファイルを動的に検索し、カテゴリを割り当てる
def get_model_paths_from_dir(model_dir: str) -> List[Tuple[str, str]]:
    found_models = []
    for filename in os.listdir(model_dir):
        if filename.endswith('.pt'):
            # ファイル名に基づいてカテゴリを推測するロジックを修正
            category = "unknown"
            lower_filename = filename.lower()
            if "ootabakoga" in lower_filename:
                category = "ootabakoga"
            elif "tomatokibaga" in lower_filename:
                category = "tomatokibaga"
            elif "tomato" in lower_filename:
                category = "tomato"
            elif "pest" in lower_filename:
                category = "pest"
            found_models.append((filename, category))
    return found_models

MODEL_PATHS = get_model_paths_from_dir(MODEL_DIR)

# モデルロード時に使用するリスト (サーバー起動時にメモリにロード)
yolo_model_list: List[Tuple[YOLO, str, str]] = [] # YOLOオブジェクト, カテゴリ, モデルファイル名

# --- サーバー起動時に一度だけ実行される初期化処理 ---
def load_models():
    """MODEL_PATHSに指定されたすべてのYOLOv8モデルをロードする"""
    print("--- YOLOv8モデルの初期化中 ---")
    
    # グローバルリストをクリア（念のため）
    yolo_model_list.clear() 

    for model_name, category in MODEL_PATHS: # model_name は "tomato_best.pt" など
        full_path = os.path.join(MODEL_DIR, model_name)
        
        if not os.path.exists(full_path):
            print(f"❌ モデルファイルが見つかりません: {full_path}")
            # モデルが見つからない場合は、推論時にエラーを発生させるため、ロードはスキップ
            continue

        try:
            # YOLOモデルをロード
            model = YOLO(full_path)
            yolo_model_list.append((model, category, model_name)) # モデルファイル名も保存
            print(f"✅ モデルロード成功: {model_name} (カテゴリ: {category})")
        except Exception as e:
            print(f"❌ モデルのロード中にエラーが発生しました ({model_name}): {e}")
            
    if not yolo_model_list:
        # 少なくとも1つモデルがないと推論できないため、エラーとして扱う
        raise ConnectionError("AIモデルのロードに失敗しました。ファイルパスとファイル名を確認してください。")

# サーバー起動時にこの関数を呼び出す必要があるため、外部から呼び出せるようにしておく
# NOTE: 適切なタイミングで routes.py や app.py から load_models() を呼び出す必要があります。

# --- 推論実行ロジック ---
def run_detection_and_analyze(image_path: str) -> Tuple[str, float, List[Dict[str, Any]], Any, str]: # 戻り値に画像データとファイル名を追加
    """
    ロード済みのすべてのモデルで推論を実行し、結果を統合・分析して返す。
    routes.py が期待する3つの値を返すように修正。
    """
    if not yolo_model_list:
        raise ConnectionError("YOLOv8モデルがロードされていません。")

    all_detections: List[Dict[str, Any]] = []
    
    # 元の画像を読み込み、描画のために使用
    original_img = cv2.imread(image_path)
    if original_img is None:
        print(f"ERROR: 画像ファイルの読み込みに失敗しました: {image_path}")
        return "健康 (エラー)", 0.0, [], None, os.path.basename(image_path) # 画像データとファイル名を返す

    # 描画用の一時画像をコピー
    drawn_img = original_img.copy()

    # --- 1. すべてのモデルで推論を実行し、all_detectionsに結果を統合 ---
    for model, category, model_filename in yolo_model_list: 
            results = model(image_path)
            
            # 結果の解析
            if results and results[0].boxes:
                r = results[0]
                
                for box in r.boxes:
                    class_id = int(box.cls.item())
                    confidence = round(box.conf.item(), 3)
                    class_name = model.names[class_id] 
                    
                    # バウンディングボックス座標 (xyxy) を整数に変換
                    x_min, y_min, x_max, y_max = [int(x) for x in box.xyxy[0].tolist()]

                    # 検出されたバウンディングボックスを描画
                    color = (0, 255, 0) # 緑色
                    thickness = 2
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.7
                    cv2.rectangle(drawn_img, (x_min, y_min), (x_max, y_max), color, thickness)
                    label = f"{class_name} ({confidence:.2f})";
                    cv2.putText(drawn_img, label, (x_min, y_min - 10), font, font_scale, color, thickness)

                    all_detections.append({
                        "disease": f"{class_name} ({category})", 
                        "confidence": confidence,
                        "model_category": category, 
                        "model_filename": model_filename, 
                        "box": {
                            "x_min": x_min, "y_min": y_min, "x_max": x_max, "y_max": y_max
                        }
                    })
    
    # 描画された画像を一時保存フォルダに保存するロジックを削除
    # original_filename = os.path.basename(image_path)
    # unique_filename = f"detected_{uuid.uuid4()}_{original_filename}"
    # temp_output_path = os.path.join(TEMP_INFERENCE_RESULTS_DIR, unique_filename)
    # cv2.imwrite(temp_output_path, drawn_img)
    # print(f"✅ 推論結果描画画像を一時保存しました: {temp_output_path}")

    # --- 2. 結果の集約と整形 ---
    if not all_detections:
        return "健康 (検出なし)", 1.0, [], drawn_img, os.path.basename(image_path) # 画像データとファイル名を返す

    filtered_detections = [
        d for d in all_detections
        if d["confidence"] <= 0.75
    ]

    if not filtered_detections:
        return "健康 (正常)", 1.0, all_detections, drawn_img, os.path.basename(image_path) # 画像データとファイル名を返す

    best_detection = max(filtered_detections, key=lambda d: d["confidence"])

    final_disease = best_detection["disease"]
    final_confidence = best_detection["confidence"]

    return final_disease, final_confidence, all_detections, drawn_img, os.path.basename(image_path) # 画像データとファイル名を返す

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
