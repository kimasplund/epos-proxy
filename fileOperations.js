
const fs = require('fs/promises');
const path = require('path');
const config = require('./config.json');

async function savePrintData(data, target, datePart) {
  try {
    const dir = path.join(config.savePath, target, datePart);
    await fs.mkdir(dir, { recursive: true });
    const filePath = path.join(dir, `${Date.now()}.xml`);  // Save as .xml file
    await fs.writeFile(filePath, data);
  } catch (error) {
    console.error('Error saving print data:', error);
  }
}

async function deleteOldPrintFiles() {
  try {
    const directories = await fs.readdir(config.savePath, { withFileTypes: true });

    for (const dir of directories) {
      if (dir.isDirectory()) {
        const dirPath = path.join(config.savePath, dir.name);
        const files = await fs.readdir(dirPath);

        for (const file of files) {
          const filePath = path.join(dirPath, file);
          const stats = await fs.stat(filePath);

          const now = Date.now();
          const fileAge = now - stats.mtimeMs;
          const retentionPeriod = config.printFileRetentionDays * 24 * 60 * 60 * 1000;  // Convert days to milliseconds

          if (fileAge > retentionPeriod) {
            await fs.unlink(filePath);
            console.log(`Deleted old print file: ${filePath}`);
          }
        }
      }
    }
  } catch (error) {
    console.error('Error deleting old print files:', error);
  }
}

module.exports = { savePrintData, deleteOldPrintFiles };
