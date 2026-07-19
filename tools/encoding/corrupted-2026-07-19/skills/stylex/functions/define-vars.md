# define-vars

**Tags:** stylex, defineVars, tokens, css-variables, theme-vars
**When to use:** 瀹氫箟涓€缁勮法缁勪欢澶嶇敤鐨勮璁′护鐗?棰滆壊 / 闂磋窛 / 瀛楀彿 / 鍦嗚)銆?
## API

```ts
const tokens = stylex.defineVars({
  bg:        '#fff',
  text:      '#000',
  brand:     '#5b6cff',
  radius:    '12px',
});
// 杩斿洖 { bg: '--bg-x1', text: '--text-x2', ... } 缂栬瘧鏃舵槧灏勫埌 CSS variables
```

## Minimal example

```tsx
// 鈿?蹇呴』鍦?.stylex.ts 鍚庣紑鏂囦欢閲?涓?export const(瑙佹殫鍧戝崱鐗?
import * as stylex from '@stylexjs/stylex';

export const tokens = stylex.defineVars({
  bg:        '#ffffff',
  surface:   '#f7f7fa',
  text:      '#1c1c1e',
  brand:     '#5b6cff',
  radius:    '12px',
});

// 鐢ㄦ硶:鍦?stylex.create 閲屽紩鐢?const styles = stylex.create({
  card: {
    backgroundColor: tokens.bg,
    color: tokens.text,
    borderRadius: tokens.radius,
  },
});
```

## 缂栬瘧鏈熸槧灏?
- `tokens.bg` 鍦ㄧ紪璇戞椂鍙樻垚 `--bg-x1`(鑷姩 hash)
- 杩愯鏃?DOM 涓婅兘鐪嬪埌 `style="--bg-x1: #fff"`
- 鍚屽悕 token 鍦ㄤ笉鍚屾枃浠?hash 涓嶅悓,璺ㄦ枃浠朵笉浼氬啿绐?
## Gotchas

- 鈿?鏂囦欢鍚庣紑蹇呴』鏄?`.stylex.ts` 璇﹁ [`.stylex.ts-filename-rule`](./.stylex.ts-filename-rule.md)
- 鈿?蹇呴』 `export const`,璇﹁ [`define-vars-must-be-export`](./define-vars-must-be-export.md)
- 涓嶈鎶?`defineVars` 鍐欏湪 component 鏂囦欢閲?瀵艰嚧 hash 绠椾笉鍑烘潵)
- tokens 鍊煎彧鑳芥槸 string / number,涓嶈兘浼犲嚱鏁?/ 瀵硅薄

## See also

- [`create-theme`](./create-theme.md)
- [`.stylex.ts-filename-rule`](./.stylex.ts-filename-rule.md)
- [`define-vars-must-be-export`](./define-vars-must-be-export.md)