# Source MEMORY.md (2026-07-15)

```
## 2026-07-15 02:30锛欴-127.B ship (route_to_team() CLI 鍙傛暟 BUG 淇)

[imp=0.85]
[cat=decision|bug-fix|ship]

### 瑙﹀彂
User 闂?"team d 鏄€庝箞鍒ゆ柇鎴戠粰鐨勪换鍔¤蛋涓嶈蛋鎼滅储鍥㈤槦鐨?,瑙﹀彂浜嗗 routing 鏈哄埗鐨勬繁搴﹀璁?(Task D-127.B)銆?

### 鍙戠幇 bug
瀹炶窇 dispatch 娴嬭瘯 5 涓?case (鎼?娲?璁ㄨ/鎷?鍋?app):

**淇鍓?* (route_to_team() v0.6 鍘熷):
- `team-b`: 浼?`--task <T>` 浣?team-b 鐨?argparse 瀹為檯鍙帴鍙?`--query` 鈫?rc=2
- `team-c`: 浼?`--mode discuss` 浣?team-c 娌℃湁 `--mode` 鈫?rc=2
- 閿欒閲嶅鍫嗙Н `.workspace/state/team-d-routing-errors.jsonl` (2.8 KB)

**淇鍚?* (route_to_team() v0.6.2, D-127.B):
- `team-b`: `--query` 鏇夸唬 `--task`
- `team-c`: 鍒犻櫎 `--mode discuss`
- 5/5 case rc=0 (team-b 脳2 / team-c / team-g / qa 榛樿)

### 鏀瑰姩鏂囦欢
- `team-d-orchestrator.py` `route_to_team()` 绗?526-538 琛? team-b + team-c 涓ゆ潯 if/elif 鏀?4 琛?

### 鍚屾椂鍙戠幇鐨勯潤榛樼己闄?(鏈慨,璁颁负鍚庣画)
- `team-c-orchestrator.py` main 榛樿 `--provider=stub`: 鍗充娇鐢ㄦ埛璇?璁ㄨ杩欎釜鏂规",瀹為檯璺戜篃鏄?stub 鍋囪璁?涓嶄細璋冪湡 LLM
- 淇硶: 鏀?default `stub` 鈫?`local` (閫夐」 `stub`/`local`)
- 鏃舵満: 鐢ㄦ埛璇?鍥㈤槦璁ㄨ瑕佺湡 LLM 璺? 鈫?1 min 鏀?+ 閲嶈窇楠岃瘉

### 鍏抽敭鍐崇瓥
- Team G rc=0 涓€鐩?OK (鍙傛暟鏃╁氨瀵? 鈫?涓嶅姩
- Team E / Team F 鍙傛暟涔?OK 鈫?涓嶅姩
- Team A / Assistant 璧?PowerShell, 缁曡繃 Python orchestrator 鈫?涓嶅姩

### 娴嬭瘯鏂规硶 (鐢ㄦ埛鍙敤)
```powershell
python team-d-orchestrator.py --mode dispatch --task "鎼滅储 vibe-trading"
# 搴旇杩斿洖 team=team-b rc=0
```

### 涓嬫鍚姩鐐?
- 鐢ㄦ埛璇?"team-c 鐪?LLM 璺? 鈫?鏀?`--provider=stub` 榛樿鍊间负 `local`, 1 min
- 鐢ㄦ埛璇?"routing-errors 娓呯┖" 鈫?鍒?`.workspace/state/team-d-routing-errors.jsonl`
- 鐢ㄦ埛璇?"test team-d 鐪熼摼璺? 鈫?璺?5 涓?case 鍏ㄩ儴 rc=0, 宸查€氳繃 2026-07-15 02:30

### 鏁欒
- 璺?file CLI 璋冪敤寰堝鏄撳弬鏁伴敊閰?鈫?璇ユ湁 unit test 璺?dispatch + assert rc=0
- v0.6 鍔?`route_to_team()` 娌＄湡楠岃瘉, 鑷充粖鎵嶈鍙戠幇 (鍩?~30 澶?

```
