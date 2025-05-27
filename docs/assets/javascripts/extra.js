document$.subscribe(function () {
  const checkboxes = document.querySelectorAll(
    '.multi-select-provider input[type="checkbox"]',
  );
  const tables = document.querySelectorAll("table");
  let hideableColumnIndexes = new Map(); // Stores column mappings per table

  // Map checkbox values to column indexes for each table
  function mapColumns() {
    hideableColumnIndexes.clear(); // Reset mapping

    tables.forEach((table) => {
      const tableMap = new Map();
      const headerCells = table.querySelectorAll("thead tr th");

      checkboxes.forEach((checkbox) => {
        const columnName = checkbox.value.trim();
        const columnIndex = Array.from(headerCells).findIndex(
          (th) => th.textContent.trim() === columnName,
        );
        if (columnIndex !== -1) {
          tableMap.set(columnName, columnIndex);
        }
      });

      hideableColumnIndexes.set(table, tableMap);
    });
  }

  // Load saved selections from localStorage
  function loadSelections() {
    const savedSelections =
      JSON.parse(localStorage.getItem("selectedProviders")) || {};
    checkboxes.forEach((checkbox) => {
      if (savedSelections.hasOwnProperty(checkbox.value)) {
        checkbox.checked = savedSelections[checkbox.value];
      }
    });
    updateTableColumns();
  }

  // Save selections to localStorage
  function saveSelections() {
    const selections = {};
    checkboxes.forEach((checkbox) => {
      selections[checkbox.value] = checkbox.checked;
    });
    localStorage.setItem("selectedProviders", JSON.stringify(selections));
  }

  // Show/Hide table columns for each table based on selected checkboxes
  function updateTableColumns() {
    if (!tables.length) return;
    mapColumns(); // Refresh column mappings

    tables.forEach((table) => {
      const tableMap = hideableColumnIndexes.get(table);
      if (!tableMap) return;

      table.querySelectorAll("tr").forEach((row) => {
        row.querySelectorAll("th, td").forEach((cell, index) => {
          const columnName = [...tableMap.keys()].find(
            (name) => tableMap.get(name) === index,
          );
          if (columnName) {
            const checkbox = Array.from(checkboxes).find(
              (cb) => cb.value === columnName,
            );
            if (checkbox) {
              cell.style.display = checkbox.checked ? "" : "none";
            }
          }
        });
      });
    });
  }

  // Event listener for checkbox changes
  checkboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", function () {
      saveSelections();
      updateTableColumns();
    });
  });

  // Initialize on page load
  mapColumns();
  loadSelections();

    const COLUMN_TO_STRETCH = "Description"; // Change this to the column name you want to stretch

    function stretchColumn() {
        tables.forEach(table => {
            const parentDiv = table.closest(".md-typeset__table");
            if (parentDiv) {
                parentDiv.style.width = "100%"; // Ensure parent div takes full width
            }

            const headerCells = table.querySelectorAll("thead tr th");
            const columnIndex = Array.from(headerCells).findIndex(th => th.textContent.trim() === COLUMN_TO_STRETCH);

            if (columnIndex === -1) return; // Exit if column is not found

            // Reset all column widths to auto first
            table.style.width = "100%"; // Ensure table stretches within the div
            table.querySelectorAll("tr").forEach(row => {
                row.querySelectorAll("th, td").forEach(cell => {
                    cell.style.width = "auto";
                });
            });

            // Get total table width
            const tableWidth = table.parentElement.clientWidth;
            let otherColumnsWidth = 0;

            // Calculate width taken by other columns
            headerCells.forEach((th, index) => {
                if (index !== columnIndex) {
                    otherColumnsWidth += th.offsetWidth;
                }
            });

            // Calculate new width for the stretched column
            const stretchedWidth = Math.max(tableWidth - otherColumnsWidth, 100); // Ensure reasonable min width

            // Apply new width to the stretched column
            table.querySelectorAll("tr").forEach(row => {
                const cells = row.querySelectorAll("th, td");
                if (cells[columnIndex]) {
                    cells[columnIndex].style.width = `${stretchedWidth}px`;
                }
            });
        });
    }

    // Run when the page loads
    stretchColumn();

    // Update on window resize for responsiveness
    window.addEventListener("resize", stretchColumn);
});
