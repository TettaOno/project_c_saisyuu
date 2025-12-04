/**
 * 検出結果に基づいてCanvas上にバウンディングボックスとラベルを描画する。
 *
 * @param {Array<Object>} detections - YOLOv8から返された検出結果のリスト
 * @param {Object} sharedElements - main.jsから渡されるHTML要素とコンテキスト
 */
export function drawBoxes(detections, sharedElements) {
    const { previewImage, canvas, ctx } = sharedElements;

    if (!ctx || !previewImage || !canvas) {
        console.error("Canvas描画に必要な要素が不足しています。");
        return;
    }
    
    // 描画をクリア
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    if (!detections || detections.length === 0) {
        canvas.style.display = 'none';
        return;
    }

    // -----------------------------------------------------------------
    // Canvasのサイズ設定
    // -----------------------------------------------------------------
    // Canvasの「ピクセル数」を画像の「本来のピクセル数」に合わせる (描画の正確性を保証)
    canvas.width = previewImage.naturalWidth;
    canvas.height = previewImage.naturalHeight;
    
    // CSSで見た目のサイズを画像に合わせる (表示のレスポンシブ性を維持)
    // previewImage.onloadイベントで設定される値をここで確実に取得
    canvas.style.width = previewImage.clientWidth + 'px';
    canvas.style.height = previewImage.clientHeight + 'px';
    canvas.style.display = 'block';

    // -----------------------------------------------------------------
    // 検出枠の描画
    // -----------------------------------------------------------------
    detections.forEach((detection, index) => {
        const box = detection.box;
        
        // 検出枠の描画設定
        // 検出結果が複数ある場合、色を変えて区別しやすくする
        ctx.strokeStyle = index % 2 === 0 ? '#FF3333' : '#3333FF'; // 赤または青
        ctx.lineWidth = 5;
        
        // 矩形（バウンディングボックス）の描画
        // boxの座標はYOLOv8から返る画像ピクセル値であることを前提とする
        const x = box.x_min;
        const y = box.y_min;
        const width = box.x_max - x;
        const height = box.y_max - y;
        
        ctx.strokeRect(x, y, width, height);

        // -------------------------------------------------------------
        // ラベル（病名と確信度）の描画
        // -------------------------------------------------------------
        const label = `${detection.disease} (${(detection.confidence * 100).toFixed(1)}%)`;
        
        ctx.fillStyle = ctx.strokeStyle;
        ctx.font = 'bold 36px Arial';
        
        // テキストの背景を描画（見やすくするため）
        const textMetrics = ctx.measureText(label);
        const textHeight = parseInt(ctx.font, 10);
        
        ctx.fillRect(x, y - textHeight - 15, textMetrics.width + 10, textHeight + 10);
        
        // テキストの色を白に変更
        ctx.fillStyle = 'white'; 
        
        // 矩形の上にテキストを配置
        ctx.fillText(label, x + 5, y - 5); 
    });
}