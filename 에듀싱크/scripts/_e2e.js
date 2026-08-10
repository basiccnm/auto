(() => JSON.stringify({
  screenH: screen.height, innerH: innerHeight, dpr: devicePixelRatio,
  cssScreenH: Math.round(screen.height), 물리높이나누기dpr: Math.round(2376/devicePixelRatio),
  saT: getComputedStyle(document.documentElement).getPropertyValue("--sa-top").trim(),
}))();
