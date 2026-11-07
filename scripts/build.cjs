const fs = require("node:fs");
fs.rmSync("dist", { recursive: true, force: true });
fs.mkdirSync("dist");
for (const file of [
  "index.html",
  "styles.css",
  "app.js",
  "favicon.svg",
  ".nojekyll",
  "vendor",
])
  fs.cpSync(file, `dist/${file}`, { recursive: true });
console.log("Static site built in dist/");
