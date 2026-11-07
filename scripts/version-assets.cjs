// Keep Pages' cached assets separate for each content revision.
// Run before committing changes because Pages serves the repository root.
const fs = require("node:fs");
const crypto = require("node:crypto");
const files = ["styles.css", "app.js", "vendor/feather.min.js"];
let html = fs.readFileSync("index.html", "utf8");
for (const file of files) {
  const hash = crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex")
    .slice(0, 12);
  const escaped = file.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  html = html.replace(
    new RegExp(`(\\./${escaped})(?:\\?v=[a-f0-9]+)?`, "g"),
    `$1?v=${hash}`,
  );
}
fs.writeFileSync("index.html", html);
console.log("Asset versions updated.");
