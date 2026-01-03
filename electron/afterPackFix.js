const fs = require("fs");
const path = require("path");

exports.default = async function (context) {
  const appName = context.packager.appInfo.productFilename;
  const pythonBin = path.join(
    context.appOutDir,
    `${appName}.app`,
    "Contents",
    "Resources",
    "python",
    "bin",
    "python3"
  );

  try {
    fs.chmodSync(pythonBin, 0o755);
    console.log("✅ Embedded Python executable");
  } catch (e) {
    console.error("❌ afterPackFix failed:", pythonBin);
  }
};