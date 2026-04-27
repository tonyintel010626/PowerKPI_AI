// CW PRO MAX logo — three colour sections
//
// left  = "CW"  (dim / textMuted)   — 11 chars wide (C:5 + gap:1 + W:5)
// mid   = "PRO" (accent / primary)  — 17 chars wide (P:5 + gap:1 + R:5 + gap:1 + O:5)
// right = "MAX" (bold / text)       — 17 chars wide (M:5 + gap:1 + A:5 + gap:1 + X:5)
//
// Letter grid: 5 wide × 4 tall, using █ ▀ ▄ and space only for clarity.
//
// C (5w):            W (5w):
//  ███               █   █
// █                  █   █
// █                  █ █ █
//  ███               ██ ██
//
// P (5w):            R (5w):            O (5w):
// ████               ████                ███
// █   █              █   █              █   █
// ████               ████               █   █
// █                  █   █               ███
//
// M (5w):            A (5w):            X (5w):
// █   █               ███              █   █
// ██ ██              █   █              █ █
// █ █ █              █████               █
// █   █              █   █              █ █
//                                      █   █

export const logo = {
  // "CW" — 4 rows × 11 chars
  left: [
    " ███  █   █",
    "█     █   █",
    "█     █ █ █",
    " ███  ██ ██",
  ],
  // "PRO" — 4 rows × 17 chars
  mid: [
    "████  ████   ███ ",
    "█   █ █   █ █   █",
    "████  ████  █   █",
    "█     █   █  ███ ",
  ],
  // "MAX" — 4 rows × 17 chars
  right: [
    "█   █  ███  █   █",
    "██ ██ █   █  █ █ ",
    "█ █ █ █████   █  ",
    "█   █ █   █  █ █ ",
  ],
}

// Mini "CW" icon shown on the go/subagent screen (left=C dim, right=W bright)
export const go = {
  left: ["    ", " ██ ", "█   ", " ██ "],
  right: ["    ", "█  █", "████", "█  █"],
}

export const marks = "_^~,"
