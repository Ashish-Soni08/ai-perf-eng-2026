import { execSync } from "child_process";

console.log("Running pnpm install...");
try {
  const result = execSync("pnpm install", {
    cwd: "/vercel/share/v0-project",
    stdio: "pipe",
    timeout: 120000,
  });
  console.log(result.toString());
  console.log("Install complete!");
} catch (err) {
  console.error("Install failed:", err.stderr?.toString() || err.message);
  // Try npm as fallback
  console.log("Trying npm install as fallback...");
  try {
    const result2 = execSync("npm install --legacy-peer-deps", {
      cwd: "/vercel/share/v0-project",
      stdio: "pipe",
      timeout: 120000,
    });
    console.log(result2.toString());
    console.log("npm install complete!");
  } catch (err2) {
    console.error("npm install also failed:", err2.stderr?.toString() || err2.message);
  }
}
