import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");

const workbookPath =
  process.argv[2] ??
  path.join(repoRoot, "data", "processed", "thesis_benchmark_selected_24_hybrid_v6_manual.xlsx");
const benchmarkPath =
  process.argv[3] ??
  path.join(repoRoot, "benchmarks", "thesis_benchmark_selected_24.json");
const previewPath =
  process.argv[4] ??
  path.join(repoRoot, "data", "processed", "thesis_benchmark_selected_24_hybrid_v6_manual_preview.png");

const workbookBlob = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(workbookBlob);

const benchmarkPayload = JSON.parse(await fs.readFile(benchmarkPath, "utf8"));
const expectedSqlByCaseId = new Map(
  benchmarkPayload.map((item) => [
    item.case_id,
    item.expectation?.reference_sql ?? "",
  ]),
);

const worksheet = workbook.worksheets.getItem("Benchmark");
const usedRange = worksheet.getUsedRange();
const usedValues = usedRange.values;

if (!usedValues?.length) {
  throw new Error("La hoja Benchmark no contiene datos.");
}

const rowCount = usedValues.length;
const existingColumnCount = usedValues[0].length;
const sourceSqlColumnLetter = "F";
const targetSqlColumnLetter = "T";

// Copiamos el formato de la columna SQL generada para mantener coherencia visual.
worksheet
  .getRange(`${sourceSqlColumnLetter}1:${sourceSqlColumnLetter}${rowCount}`)
  .copyTo(worksheet.getRange(`${targetSqlColumnLetter}1:${targetSqlColumnLetter}${rowCount}`), "all");

const targetRange = worksheet.getRange(`${targetSqlColumnLetter}1:${targetSqlColumnLetter}${rowCount}`);
const targetValues = [];

for (let rowIndex = 0; rowIndex < rowCount; rowIndex += 1) {
  if (rowIndex === 0) {
    targetValues.push(["SQL_esperada"]);
    continue;
  }

  const caseId = usedValues[rowIndex]?.[0];
  targetValues.push([expectedSqlByCaseId.get(caseId) ?? ""]);
}

targetRange.values = targetValues;
targetRange.format.wrapText = true;
targetRange.format.columnWidthPx = 360;

// Ajustamos el encabezado para que visualmente acompañe al resto de columnas.
worksheet.getRange(`${targetSqlColumnLetter}1`).format = {
  ...worksheet.getRange("F1").format,
};

const preview = await workbook.render({
  sheetName: "Benchmark",
  range: `A1:${targetSqlColumnLetter}${Math.min(rowCount, 8)}`,
  scale: 1,
  format: "png",
});

await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(workbookPath);

console.log(JSON.stringify({ workbookPath, benchmarkPath, previewPath, rowCount, existingColumnCount }));
