// =================================================================
// 1. グローバル要素の取得 (DOMContentLoadedイベント前に宣言のみ)
// これらの変数はDOMContentLoaded内で初期化されます
// =================================================================
let fileInput;
let detectButton;
let previewImage;
let resultElement;
let canvas;
let ctx; 

// =================================================================
// 2. イベントハンドラ: 画像選択時のプレビュー表示
// (この関数はHTMLから直接参照されるため、グローバルスコープに残す)
// =================================================================
function previewFile() {
    // DOMContentLoaded内で初期化されていることを確認
    if (!fileInput) {
        console.error("【致命的エラー】HTML要素の初期化が完了していません。");
        return;
    }

    // ファイルが選択されているか再確認
    const file = fileInput.files[0];
    
    if (canvas) {
        canvas.style.display = 'none';
    }
    
    // 必須要素のチェック
    if (!fileInput || !detectButton || !previewImage || !resultElement) {
         console.error("【致命的エラー】必要なHTML要素が見つかりません。HTMLのIDを確認してください。");
         return;
    }

    if (file) {
        const reader = new FileReader();
        
        reader.onerror = function (e) {
            console.error("FileReaderでエラーが発生しました:", e.target.error);
            resultElement.innerHTML = `<p style="color: red;">❌ 画像ファイルの読み込みエラーが発生しました。</p>`;
            previewImage.style.display = 'none';
            detectButton.disabled = true;
        };

        reader.onload = function (e) {
            previewImage.src = e.target.result;
            previewImage.style.display = 'block';
            detectButton.disabled = false; // ファイルが選択されたらボタンを有効化
        };
        reader.readAsDataURL(file);
        resultElement.innerHTML = `画像「${file.name}」が選択されました。判定ボタンを押してください。`;
    } else {
        previewImage.style.display = 'none';
        detectButton.disabled = true; // ファイルがない場合はボタンを無効化
        resultElement.innerHTML = "ファイルを選択してください。";
    }
}


// =================================================================
// 3. 画像送信ロジック (YOLOv8 APIへの POST)
// (この関数はHTMLから直接参照されるため、グローバルスコープに残す)
// =================================================================
function uploadImage() {
    // DOMContentLoaded内で初期化されていることを確認
    if (!fileInput) {
        console.error("【致命的エラー】HTML要素の初期化が完了していません。");
        return;
    }
    
    const file = fileInput.files[0];

    if (!file) {
        console.error('画像ファイルが選択されていません。');
        return;
    }

    resultElement.innerHTML = "画像をサーバーに送信中... 📤";
    detectButton.disabled = true; // 二重送信防止のため無効化

    const formData = new FormData();
    formData.append('file', file); 

    // Fetch APIでバックエンドAPIへPOSTリクエストを送信
    fetch('/api/detect-disease', { 
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            // エラー発生時、サーバーからの詳細なエラーメッセージを取得
            return response.text().then(text => { throw new Error(`HTTP Error! Status: ${response.status}. Detail: ${text}`); });
        }
        return response.json(); // JSON形式で結果を解析
    })
    .then(data => {
        console.log("受信データ:", data);
        
        displayResultText(data);
        drawBoxes(data.detections);
    })
    .catch(error => {
        console.error('送信または解析エラー:', error);
        resultElement.innerHTML = `
            <p style="color: red;">❌ **通信エラーまたは処理に失敗**</p>
            <p>詳細: ${error.message.substring(0, 150)}...</p>
        `;
        if (canvas) {
            canvas.style.display = 'none'; // Canvas非表示
        }
    })
    .finally(() => {
        detectButton.disabled = false; // ボタンを再度有効化
    });
}


// =================================================================
// DOMContentLoaded イベントで全体をラップ
// HTML要素がすべて読み込まれた後にJSを実行することを保証
// =================================================================
document.addEventListener('DOMContentLoaded', () => {

    // 1. グローバル変数の初期化
    fileInput = document.getElementById('tomatoImage');
    detectButton = document.getElementById('detectButton');
    previewImage = document.getElementById('preview');
    resultElement = document.getElementById('result');
    canvas = document.getElementById('detectionCanvas');
    ctx = canvas ? canvas.getContext('2d') : null; 

    // 2. 初期メッセージ設定
    if (resultElement) {
        resultElement.innerHTML = "ファイルを選択してください。";
    }
    
    // -------------------------------------------------------------
    // 以下はDOMContentLoaded内のローカルスコープで定義されるヘルパー関数
    // -------------------------------------------------------------

    // 検出結果のテキストをHTMLに反映する
    function displayResultText(data) {
        const confidencePercent = (data.confidence * 100).toFixed(1) + '%';
        const dbStatusColor = data.db_status === "成功" ? "green" : "red";
        const diseaseCount = data.detections ? data.detections.length : 0;

        let html = `
            <h3>✅ 判定結果</h3>
            <p>全体の病気の可能性: <strong>${data.disease}</strong></p>
            <p>最高確信度: ${confidencePercent}</p>
            <p>検出された病変の数: ${diseaseCount}</p>
            <hr>
            <h4>データベース処理</h4>
            <p>ステータス: <strong style="color: ${dbStatusColor};">${data.db_status}</strong></p>
            <p>詳細: <em>${data.db_detail}</em></p>
        `;
        resultElement.innerHTML = html;
    }

    // 検出枠を描画する
    function drawBoxes(detections) {
        if (!ctx || !previewImage || !canvas) return;
        
        // 描画をクリア
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (!detections || detections.length === 0) {
            canvas.style.display = 'none';
            return;
        }

        // Canvasのサイズを画像の「本来のサイズ」に合わせる (ピクセル座標が一致するため)
        canvas.width = previewImage.naturalWidth;
        canvas.height = previewImage.naturalHeight;
        
        // CSSで見た目のサイズを画像に合わせる (CSSが適用された後の要素サイズ)
        canvas.style.width = previewImage.clientWidth + 'px';
        canvas.style.height = previewImage.clientHeight + 'px';
        canvas.style.display = 'block';

        detections.forEach((detection, index) => {
            const box = detection.box;

            // 検出枠の描画設定
            ctx.strokeStyle = index % 2 === 0 ? '#FF3333' : '#3333FF'; // 赤または青
            ctx.lineWidth = 5;
            
            // 矩形（バウンディングボックス）の描画: (x, y, width, height)
            const width = box.x_max - box.x_min;
            const height = box.y_max - box.y_min;
            ctx.strokeRect(box.x_min, box.y_min, width, height);

            // ラベル（病名と確信度）の描画
            const label = `${detection.disease} (${(detection.confidence * 100).toFixed(1)}%)`;
            
            ctx.fillStyle = ctx.strokeStyle;
            ctx.font = 'bold 36px Arial'; // 文字サイズを調整
            
            // 矩形の上にテキストを配置
            ctx.fillText(label, box.x_min + 5, box.y_min - 10); 
        });
    }
});
