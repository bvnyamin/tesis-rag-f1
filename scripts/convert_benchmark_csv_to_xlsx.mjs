import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

async function main() {
  const [inputPath, outputPath, previewPath] = process.argv.slice(2);

  if (!inputPath || !outputPath) {
    throw new Error("Uso: node convert_benchmark_csv_to_xlsx.mjs <input.csv> <output.xlsx> [preview.png]");
  }

  const csvText = await fs.readFile(inputPath, "utf8");
  const workbook = await Workbook.fromCSV(csvText, { sheetName: "Benchmark" });
  const sheet = workbook.worksheets.getItem("Benchmark");
  const usedRange = sheet.getUsedRange();

  sheet.freezePanes.freezeRows(1);
  sheet.showGridLines = false;

  usedRange.format.autofitColumns();
  usedRange.format.autofitRows();

  const headerRange = sheet.getRange(`A1:${_columnIndexToLetter(_countColumns(csvText))}1`);
  headerRange.format = {
    fill: "#1F4E78",
    font: { bold: true, color: "#FFFFFF" },
  };

  usedRange.format.borders = {
    preset: "all",
    style: "thin",
    color: "#D9E2F3",
  };

  const outputDir = path.dirname(outputPath);
  await fs.mkdir(outputDir, { recursive: true });

  if (previewPath) {
    const preview = await workbook.render({
      sheetName: "Benchmark",
      autoCrop: "all",
      scale: 1,
      format: "png",
    });
    await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
  }

  const xlsx = await SpreadsheetFile.exportXlsx(workbook);
  await xlsx.save(outputPath);
}

function _countColumns(csvText) {
  const firstLine = csvText.split(/\r?\n/, 1)[0] ?? "";
  return Math.max(firstLine.split(",").length, 1);
}

function _columnIndexToLetter(columnCount) {
  let current = columnCount;
  let result = "";

  while (current > 0) {
    const remainder = (current - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    current = Math.floor((current - 1) / 26);
  }

  return result || "A";
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
