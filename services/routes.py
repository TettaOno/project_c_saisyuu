from flask import Blueprint, request, jsonify
import os
import datetime
import uuid
import time
import shutil
# AI/DBサービスを相対インポート
from .ai_service import run_detection_and_analyze
from .db_service import insert_detection_log
import cv2 # 画像処理のために追加
from typing import List, Dict, Any

# Blueprintの定義
api_bp = Blueprint('api', __name__)

# --- 設定 ---
# UPLOAD_FOLDERは app.py 側で作成済み
UPLOAD_FOLDER = 'uploads' 

PROCESSED_IMAGES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..\static\processed_images')
# 新しい定数 RESULT_FOLDER を追加し、result フォルダを指すようにします。
RESULT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'result')
os.makedirs(PROCESSED_IMAGES_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True) # result フォルダも作成

# def draw_bounding_box_and_save(
#     image_path: str,
#     detection: Dict[str, Any],
#     output_filename: str,
#     model_category: str # 新しい引数を追加
# ) -> str:
#     """
#     画像に最も確信度の高い検出結果のバウンディングボックスを描画し、一時保存する。
#     描画された画像の一時URLを返す。
#     """
#     # 画像の読み込み
#     img = cv2.imread(image_path)
#     if img is None:
#         print(f"ERROR: 画像ファイルの読み込みに失敗しました: {image_path}")
#         return ""
# 
#     # バウンディングボックスの描画
#     box = detection['box']
#     x_min, y_min, x_max, y_max = box['x_min'], box['y_min'], box['x_max'], box['x_max']
#     disease = detection['disease']
#     confidence = detection['confidence']
# 
#     # 色 (B, G, R)
#     color = (0, 255, 0) # 緑色
#     thickness = 2
#     font = cv2.FONT_HERSHEY_SIMPLEX
#     font_scale = 0.7
# 
#     # バウンディングボックス
#     cv2.rectangle(img, (x_min, y_min), (x_max, y_max), color, thickness)
# 
#     # ラベル
#     label = f"{disease}: {confidence:.2f}"
#     cv2.putText(img, label, (x_min, y_min - 10), font, font_scale, color, thickness)
# 
#     # 描画された画像をまず processed_images に保存
#     processed_filepath = os.path.join(PROCESSED_IMAGES_FOLDER, output_filename)
# 
#     try:
#         cv2.imwrite(processed_filepath, img)
#         print(f"SUCCESS: 処理済み画像を保存しました: {processed_filepath}")
#         
#         # 0.2秒の遅延を追加
#         time.sleep(0.2)
#         
#         # 検出されたカテゴリに合わせて result フォルダに移動
#         result_category_folder = os.path.join(RESULT_FOLDER, model_category)
#         os.makedirs(result_category_folder, exist_ok=True)
#         
#         # result フォルダに移動（コピーではなく移動）
#         result_filepath = os.path.join(result_category_folder, output_filename)
#         
#         # ファイルが存在することを確認してから移動
#         if os.path.exists(processed_filepath):
#             shutil.move(processed_filepath, result_filepath)
#             print(f"SUCCESS: 推論結果画像を result フォルダに移動しました: {result_filepath} (カテゴリ: {model_category})")
#         else:
#             print(f"ERROR: 移動元のファイルが見つかりません: {processed_filepath}")
#             return ""
#         
#         return f"/static/processed_images/{output_filename}"
#     except Exception as e:
#         print(f"ERROR: 処理済み画像の保存・移動中にエラーが発生しました: {e}")
#         import traceback
#         traceback.print_exc()
#         return ""
# 
# @api_bp.route('/detect-disease', methods=['POST'])
# def detect_disease_endpoint():
#     # 1. ファイル受付のチェック
#     if 'file' not in request.files:
#         return jsonify({"error": "ファイルが添付されていません"}), 400
#     
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({"error": "ファイル名が空です"}), 400
#         
#     original_filename = file.filename
#     # 一時保存用のユニークなファイル名を作成
#     unique_filename = f"{uuid.uuid4()}_{original_filename}"
#     temp_filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
#     
#     # 2. 画像の一時保存
#     try:
#         file.save(temp_filepath)
#         print(f"画像ファイル '{original_filename}' を一時保存しました。")
#     except Exception as e:
#         print(f"一時ファイル保存エラー: {e}")
#         return jsonify({"error": f"サーバー側でファイル保存に失敗しました: {e}"}), 500
# 
#     # 3. YOLOv8 推論の実行 (AIサービス呼び出し)
#     try:
#         final_disease, final_confidence, all_detections = run_detection_and_analyze(temp_filepath)
#     except Exception as e:
#         print(f"YOLOv8推論エラー: {e}")
#         # 4. エラー時も一時ファイルを削除
#         if os.path.exists(temp_filepath):
#             os.remove(temp_filepath)
#         return jsonify({"error": f"AI推論中にエラーが発生しました: {e}"}), 500
#     
#     # 4. DBサービスによるログ挿入を実行
#     db_success, db_message = insert_detection_log(
#         original_filename, 
#         final_disease, 
#         final_confidence,
#         all_detections
#     )
#     
#     # 5. 一時ファイルの削除 (この位置から移動)
#     # if os.path.exists(temp_filepath):
#     #     os.remove(temp_filepath)
#     #     print(f"一時ファイル '{temp_filepath}' を削除しました。")
#         
#     # 6. フロントエンドへの応答データの作成
#     response_data = {
#         "disease": final_disease,
#         "confidence": final_confidence,
#         "detections": all_detections,
#         "db_status": "成功" if db_success else "失敗",
#         "db_detail": db_message,
#     }
#     
#     processed_image_url = "" # 初期化
#     processed_filepath = "" # 初期化
# 
#     if all_detections: # 検出結果がある場合のみ処理済み画像を生成
#         best_detection = max(all_detections, key=lambda d: d['confidence']) # 最も確信度の高い検出結果
#         # ユニークなファイル名を生成
#         processed_filename = f"processed_{uuid.uuid4()}_{os.path.basename(original_filename)}"
#         processed_image_url = draw_bounding_box_and_save(
#             temp_filepath, best_detection, processed_filename, best_detection['model_category'] # model_category を追加
#         )
#         processed_filepath = os.path.join(PROCESSED_IMAGES_FOLDER, processed_filename)
# 
#     response_data["processed_image_url"] = processed_image_url
# 
#     print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 判定完了。DB: {db_success}")
#     
#     # 推論後、検出の有無に関わらず一時ファイルを削除
#     if os.path.exists(temp_filepath):
#         os.remove(temp_filepath)
#         print(f"一時ファイル '{temp_filepath}' を削除しました。")
#     
#     # 処理済み画像の一時ファイルを削除 (一時的にコメントアウト)
#     # if os.path.exists(processed_filepath):
#     #     os.remove(processed_filepath)
#     #     print(f"一時処理済みファイル '{processed_filepath}' を削除しました。")
# 
#     return jsonify(response_data)