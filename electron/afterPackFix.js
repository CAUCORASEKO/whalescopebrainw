const fs = require("fs");
const path = require("path");

exports.default = async function (context) {
  // Nombre base de la app (ej: WhaleScope)
  const appBaseName = context.packager.appInfo.productFilename;

  // ✅ Ahora la ruta correcta es .../Resources/python/bin/python3
  const pythonPath = path.join(
    context.appOutDir,
    appBaseName + ".app",
    "Contents",
    "Resources",
    "python",
    "bin",
    "python3"
  );

  try {
    fs.chmodSync(pythonPath, 0o755);
    console.log("✅ afterPackFix: Embedded Python marked executable");
  } catch (err) {
    console.error("❌ afterPackFix error:", err);
    console.error("⛔ PATH that failed:", pythonPath);
  }
};
