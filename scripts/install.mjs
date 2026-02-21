import { execSync } from "child_process";

try {
  console.log("Running pnpm install...");
  const output = execSync("pnpm install", {
    cwd: "/vercel/share/v0-project",
    stdio: "pipe",
    encoding: "utf-8",
    timeout: 120000,
  });
  console.log(output);
  console.log("Install complete!");
} catch (err) {
  console.error("Install failed:", err.stderr || err.message);
  console.log("stdout:", err.stdout);
}
