# SAG 瑙勫垯鎶藉彇鍣ㄦ敼閫狅紙2026-06-27 鍑屾櫒锛?

## 鑳屾櫙
SAG 鐨?extract=true 閾捐矾鍦ㄦ湰鏈?CPU 涓婅窇涓嶅姩浠讳綍 LLM锛?.5B/7B/llama3.2 閮藉け璐ワ級銆?
LocalGraph 椤圭洰鐢ㄨ鍒欓┍鍔ㄦ娊鍙栵紙姝ｅ垯 + 鍏抽敭璇嶏級瀹炵幇浜嗘棤 LLM 渚濊禆鐨勪簨浠?瀹炰綋鎻愬彇銆?

## 鏀归€犲唴瀹?

### 1. 鏂板 rules.ts锛圕:\sag-main\src\ingestion\extract\rules.ts锛?
- 7 绫诲疄浣撹鍒欙細person / work / subject / product / action / metric / location / time / organization
- 鍋滅敤璇嶈〃
- 鍏辩幇璁℃暟锛堝悓涓€瀹炰綋澶氭鍑虹幇锛?
- 6 绫?category 鎺ㄦ柇锛氱粡鍏歌В璇?/ 鏂瑰墏瑙ｆ瀽 / 杈ㄨ瘉璁烘不 / 鍖诲瑙傜偣 / 鍓傞噺閰嶄紞 / 鍦扮悊鏂囧寲 / 鏃跺簭鑰冭瘉 / 閫氱敤鐭ヨ瘑

### 2. 鏀归€?extractor.ts锛堢粺涓€鍏ュ彛锛?
- 鏂板 ExtractorMode = "rule" | "llm" | "hybrid"
- rule: 绾鍒?
- llm: 绾?LLM
- hybrid: 浼樺厛瑙勫垯锛堚墺2 瀹炰綋鏃朵娇鐢級锛屽惁鍒欏洖閫€ LLM

### 3. types.ts 鍔?extractorMode 瀛楁
### 4. api/server.ts 涓や釜 schema (ingestSchema, uploadSchema) 鍔?extractorMode
### 5. ingestion-service.ts 鍏抽敭 bug 淇
**Bug**锛氱 301 琛?`mode: extractorMode` 鍦?prepareEvents 鏂规硶閲岋紝浣?`extractorMode` 鏄埗鏂规硶 ingestDocument 鐨勫眬閮ㄥ彉閲忥紝**浣滅敤鍩熼敊璇?*銆倀sx/esbuild 涓嶅仛 scope 妫€鏌ユ墍浠ユ病鎶ラ敊锛岃繍琛屾椂鏄?undefined銆?
**淇**锛氭妸 extractorMode 浣滀负鍙傛暟浼犵粰 prepareEvents銆?

### 6. rerank-client.ts 鍏滃簳鏀瑰己
鍘熸潵锛歨asRemoteLlm=false 鎵嶈蛋 local
鐜板湪锛歨asRemoteLlm=false 鎴?RERANK_MODEL 涓虹┖鏃惰蛋 local
**閬垮厤**锛氭湰鍦版病瑁?qwen3-rerank 鏃?multi search 鎶?404

### 7. config/env.ts
RERANK_MODEL 榛樿浠?"qwen3-rerank" 鏀逛负 ""锛岄伩鍏嶈璋冭繙绋?404

## 楠岃瘉缁撴灉
- ingest (extract=true, mode=rule) 鐪熷疄楹婚粍姹ゆ枃绔狅細4 绉掑畬鎴愶紝17 涓疄浣?
- ingest (extract=true, mode=hybrid) 榛樿鏅鸿兘鍒囨崲
- search vector: 0.27 score 鍛戒腑
- search multi: 杩斿洖 queryEntities + section

## PowerShell 娴嬭瘯韪╁潙
1. ConvertTo-Json + Invoke-RestMethod锛氫細鐢熸垚 BOM锛屽鑷?SAG 鎶?"Body is not valid JSON"
2. 瑙ｅ喅锛氱敤 .NET HttpClient (Add-Type + System.Net.Http.HttpClient) + 鏃?BOM UTF-8 缂栫爜
3. 涓枃 hex 鍦?PowerShell console 鏄剧ず鏄贡鐮侊紙chcp 437锛夛紝DB 閲屽瓨鐨勬槸瀵圭殑

## 宸茬煡闄愬埗
- all-minilm 384 缁存湁 token 闄愬埗锛堝疄娴?256锛夛紝闀挎枃妗ｉ渶瑕?chunking.maxTokens=200
- 瑙勫垯鎶藉彇鐨?浜у搧"鍒嗙被浼氭妸"鍊笀璁や负楹婚粍姹?璇瘑鍒负 product锛堣椽濠尮閰嶏級锛岄渶瑕佺户缁粏鍖栨鍒?
- rules.ts 鏄?骞垮害浼樺厛"绛栫暐锛氬畞鍙鎶斤紙17 涓級锛屼笉鍑嗘椂鍐嶆紡
