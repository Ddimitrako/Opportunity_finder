import { createRequire } from "node:module";
import fs from "node:fs/promises";
import path from "node:path";

const require = createRequire(import.meta.url);
const { FileBlob, SpreadsheetFile } = require("@oai/artifact-tool");

const source = process.argv[2] ?? path.resolve("backend/catalog/software_catalog.xlsx");
const output = process.argv[3] ?? path.resolve("backend/catalog/rendered");
const blob = await FileBlob.load(source);
const workbook = await SpreadsheetFile.importXlsx(blob);
await fs.mkdir(output, { recursive: true });
for (const sheet of workbook.worksheets.items) {
  const image = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 1.2 });
  await fs.writeFile(path.join(output, `${sheet.name.replace(/[^a-z0-9]+/gi, "_")}.png`), new Uint8Array(await image.arrayBuffer()));
}
console.log(JSON.stringify({ source, output, sheets: workbook.worksheets.items.map((sheet) => sheet.name) }));
