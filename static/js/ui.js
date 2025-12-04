// api.js と canvas.js から必要な関数をインポート
// main.js からグローバル変数を受け取って使用します。

/**
 * UIの操作に必要な関数をエクスポートします。
 * @param {object} sharedElements - main.jsから渡されるHTML要素とコンテキスト
 */
export const ui = (sharedElements) => {
    const { fileInput, detectButton, previewImage, resultElement, canvas, ctx, uploadImageToApi, drawBoxes } = sharedElements;

    /**
     * 画像を選択した際のプレビュー表示とボタン有効化
     * HTMLの onchange="previewFile()" から呼び出される
     */
    const previewFile = () => {
        // ファイルが選択されているか再確認
        const file = fileInput.files[0];

        // Canvasを一旦非表示にし、以前の描画をクリア
        if (canvas) {
            canvas.style.display = 'none';
            if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
        }

        if (file) {
            const reader = new FileReader();

            reader.onerror = (e) => {
                console.error("FileReaderでエラーが発生しました:", e.target.error);
                resultElement.innerHTML = `<p style="color: red;">❌ 画像ファイルの読み込みエラーが発生しました。</p>`;
                previewImage.style.display = 'none';
                detectButton.disabled = true;
            };

            reader.onload = (e) => {
                previewImage.src = e.target.result;
                previewImage.style.display = 'block';
                detectButton.disabled = false; // ファイルが選択されたらボタンを有効化

                // プレビュー表示後、Canvasの初期サイズを設定（画像と重ねるため）
                previewImage.onload = () => {
                    canvas.width = previewImage.naturalWidth;
                    canvas.height = previewImage.naturalHeight;
                    canvas.style.width = previewImage.clientWidth + 'px';
                    canvas.style.height = previewImage.clientHeight + 'px';
                };
            };
            reader.readAsDataURL(file);
            resultElement.innerHTML = `画像「${file.name}」が選択されました。判定ボタンを押してください。`;
        } else {
            previewImage.style.display = 'none';
            detectButton.disabled = true; // ファイルがない場合はボタンを無効化
            resultElement.innerHTML = "ファイルを選択してください。";
        }
    };

    /**
     * 判定ボタンを押したときの処理（APIへの送信と結果の表示）
     * HTMLの onclick="uploadImage()" から呼び出される
     */
    const uploadImage = () => {
        const file = fileInput.files[0];

        if (!file) {
            console.error('画像ファイルが選択されていません。');
            return;
        }

        resultElement.innerHTML = "画像をサーバーに送信中... 📤";
        detectButton.disabled = true;

        // APIモジュールを呼び出して通信を開始
        uploadImageToApi(file)
            .then(data => {
                console.log("受信データ:", data);
                
                // 1. テキスト情報の表示
                displayResultText(data);
                
                // 2. Canvasへの検出枠描画 (canvasモジュールを呼び出し)
                drawBoxes(data.detections, sharedElements);
            })
            .catch(error => {
                console.error('送信または解析エラー:', error);
                resultElement.innerHTML = `
                    <p style="color: red;">❌ **通信エラーまたは処理に失敗**</p>
                    <p>詳細: ${error.message.substring(0, 150)}...</p>
                `;
                if (canvas) {
                    canvas.style.display = 'none';
                }
            })
            .finally(() => {
                detectButton.disabled = false; // ボタンを再度有効化
            });
    };

    /**
     * 検出結果のテキストをHTMLに反映するヘルパー関数
     * @param {object} data - サーバーから受信したJSONデータ
     */
    const displayResultText = (data) => {
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
    };

    // main.jsがイベントリスナーを設定できるように、外部から参照させる
    return {
        previewFile,
        uploadImage
    };
};