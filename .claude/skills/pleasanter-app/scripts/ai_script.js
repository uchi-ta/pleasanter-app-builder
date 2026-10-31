// AI機能「__TITLE__」（spec.json の ai から自動生成。手で編集しても再登録で上書きされる）
// トリガーのチェックをオンにして保存すると、レコードの内容を Claude API に送り、結果を項目に書き込む。
// サーバスクリプトは10秒で打ち切られる（Script.json の ServerScriptTimeOut）ため、速いモデルで短く答えさせる。
const CONF = __CONF__;
// API キーはこのスクリプトには書かない。共有サーバスクリプト「共通設定（APIキー）」の CLAUDE_API_KEY を使う
// （デモで画面にスクリプトを表示しても、キーが映り込まないようにするため）
function apiKey() {
    if (typeof CLAUDE_API_KEY === 'undefined' || !CLAUDE_API_KEY) throw new Error('APIキーが設定されていません（共有スクリプト「共通設定（APIキー）」を確認）');
    return CLAUDE_API_KEY;
}

function valueText(col, v, prefix) {
    if (v === null || v === undefined) return '';
    const map = CONF.choices[(prefix || '') + col];
    if (map && map[String(v)] !== undefined) return map[String(v)];
    if (v instanceof Date || (typeof v === 'object' && v.getFullYear)) {
        return v.getFullYear() < 1901 ? '' : `${v.getFullYear()}/${v.getMonth() + 1}/${v.getDate()}`;
    }
    return String(v);
}

function recordText(source, columns) {
    return columns.map(c => `- ${c.label}: ${valueText(c.name, source[c.name])}`).join('\n');
}

function relatedText() {
    if (!CONF.related) return '';
    const r = CONF.related;
    const view = { View: { ColumnFilterHash: {}, ColumnSorterHash: {} } };
    // 関連テーブルが自分自身のときは「同じ親を指す他のレコード」（例: 同じ訪問先の過去の日報）を取る
    const key = r.sameParent ? model[r.link] : model.ResultId;
    if (!key) return '';
    view.View.ColumnFilterHash[r.link] = JSON.stringify([String(key)]);
    if (r.sort) view.View.ColumnSorterHash[r.sort] = 'desc';
    const rows = items.Get(Number(r.siteId), JSON.stringify(view));
    // items.Get は .NET の配列を返すので、件数は length ではなく Length で取る
    const count = rows ? (rows.Length !== undefined ? rows.Length : rows.length) : 0;
    const list = [];
    for (let i = 0; i < count && list.length < r.limit; i++) {
        if (r.sameParent && rows[i].ResultId === model.ResultId) continue;
        list.push(r.columns.map(c => `${c.label}=${valueText(c.name, rows[i][c.name], '_rel_')}`).join(' / '));
    }
    return `\n\n## ${r.title}（新しい順に最大${r.limit}件）\n` + (list.length ? list.map(x => '- ' + x).join('\n') : '- なし');
}

function callClaude(prompt) {
    httpClient.RequestUri = 'https://api.anthropic.com/v1/messages';
    httpClient.RequestHeaders.Clear();
    httpClient.RequestHeaders.Add('x-api-key', apiKey());
    httpClient.RequestHeaders.Add('anthropic-version', '2023-06-01');
    httpClient.TimeOut = CONF.timeoutMs;
    httpClient.Content = JSON.stringify({
        model: CONF.model,
        max_tokens: CONF.maxTokens,
        output_config: { effort: CONF.effort },
        system: CONF.system,
        messages: [{ role: 'user', content: prompt }]
    });
    const text = httpClient.Post();
    if (httpClient.IsTimeOut) throw new Error('AIの応答がタイムアウトしました');
    if (!httpClient.IsSuccess) {
        const reasons = { 401: 'APIキーが正しくありません', 403: 'APIキーに権限がありません', 429: 'AIの利用が混み合っています。時間をおいて再実行してください',
                          500: 'AIのサーバでエラーが発生しました', 529: 'AIのサーバが混み合っています。時間をおいて再実行してください' };
        throw new Error(`${reasons[httpClient.StatusCode] || 'AI APIでエラーが発生しました'}（HTTP ${httpClient.StatusCode}）`);
    }
    const res = JSON.parse(text);
    if (res.stop_reason === 'refusal') throw new Error('AIが回答を控えました');
    const block = (res.content || []).find(b => b.type === 'text');
    if (!block) throw new Error('AIの応答に本文がありません');
    // JSON 以外の前後の文字（コードフェンス等）を取り除いて解釈する
    const raw = block.text;
    const json = raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1);
    return JSON.parse(json);
}

if (model[CONF.trigger] === true) {
    model[CONF.trigger] = false;
    try {
        const keys = CONF.outputs.map(o => `"${o.key}": ${o.instruction}`).join('\n');
        const prompt = `${CONF.instruction}\n\n## 対象の${CONF.tableTitle}\n${recordText(model, CONF.inputs)}${relatedText()}\n\n` +
            `## 出力形式\n次のキーを持つ JSON オブジェクトだけを出力してください（前置き・説明・コードフェンスは不要）。\n{\n${keys}\n}`;
        const out = callClaude(prompt);
        CONF.outputs.forEach(o => {
            let v = out[o.key];
            if (v === undefined || v === null) return;
            if (Array.isArray(v)) v = v.map(x => '・' + x).join('\n');
            if (o.type === 'Num') v = Number(v) || 0;
            if (o.type === 'Class' && o.allowed && o.allowed.indexOf(String(v)) < 0) return;
            model[o.column] = v;
        });
        if (CONF.stampColumn) model[CONF.stampColumn] = `${CONF.model}（${new Date().toLocaleString('ja-JP')}）`;
        context.AddMessage(`${CONF.title}: AIの結果を反映しました。`, 'alert-success');
    } catch (e) {
        context.AddMessage(`${CONF.title}: ${e.message}（保存は通常どおり行われます）`, 'alert-warning');
        context.Log(e.stack || String(e));
    }
}
