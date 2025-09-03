# DBI: Assembly Orders with TO (NC)

## BOM Report
- read BOM COmponents Availability file.

## Inventory List
- Read Inventory List file

##  Availability Report
- Read Availability Report File
- SKU as Plain text

## Quantity
- Read Quantity File

## Replenishment Report
- Read Replenishment Report

## ABC Analysis
- Read Profit File
- Rank By cumulative profit and categorize ABC Analysis by slicing 70-20-10

## Transfer (Armory to NC Main)
- Column N:
  - SKUs w/ no BOM in NC Armory.`=filter(AvailabilityReport!B:B, AvailabilityReport!D:D = "NC - Armory", AvailabilityReport!J:J>20, isna(match(AvailabilityReport!B:B,'BOM report'!B:B,0)))` List SKUs where Location is `NC-Armory`  and OnHand quantity is greater than 20 and The SKU is not in the BOM report.
- Column A to D: `=query(AvailabilityReport!A:O,"SELECT B, C, D, SUM(J) WHERE D = 'NC - Armory' AND J>20 AND B MATCHES '"&TEXTJOIN("|",true,N3:N)&"' GROUP BY B, C, D ORDER BY SUM(J) DESC")`. A summary table with columns SKU, PRoductName, Location and the aggregated sum of `OnHand` for rows in AvailabilityReport that meet all filters, grouped by the triplet SKU, PRoductName, Locatio, and sorted by the total sum of `OnHand`  descending. The filters are:
  - Location (column D) must be "NC - Armory"
  - OnHand (column J) must be greater than 20
  - SKU (column B) must match one of the values listed in SKUs w/ no BOM in NC Armory (N3:N)
- Column E - OnHand in NC - Main. `=sumifs(AvailabilityReport!J:J,AvailabilityReport!B:B,A:A,AvailabilityReport!D:D,"NC - Main")`. Sum the values from OnHand (column J) of AvailabilityReport for the SKU in this row (column A), but only where the location (column D) is NC - Main.”
- COlumns G to K - Transfer from NC - Armory to NC - Main. `=QUERY(A3:F,"SELECT A, B, C, D, E WHERE E < 20 AND F = 0",1)`. Returns SKU, Product Name, Location, sum of On Hand, OnHand in NC - Main para os casos em que On Hand on NC - Main is less than 20.

## Replenishment Computation
- Column A - SKU. `unique(query('Assembly Status Computation'!A3:W,"SELECT B WHERE U = 'Yes' AND V = 'No' AND W = 'No' AND NOT B MATCHES '2444|4300|3818|2582'",1))`. Return unique SKUs from BOM Report that matches the filters:
  - The same SKU in Inventory List has AssemblyBOM = Yes
  - The same SKU in Inventory List has AutoAssembly = No
  - The same SKU in Inventory List has AutoDisassembly = No
  - Is not any of the following: 2444|4300|3818|2582
- Column B - Number of Components: or each SKU in column A of Replenishment Computation, count how many times it appears in column B of BOM report.”
- OnHand: Returns the total OnHand quantity from AvailabilityReport!J:J for each SKU in column A, summed across the three locations: NC - Main, NC - Armory, and NC - FFL.
- OnOrder: Returns the total from column OnOrder of AvailabilityReport for each SKU in column A, summed across the three locations: NC - Main, NC - Armory, and NC - FFL.
-InTransit: Returns the sum of values in column N of AvailabilityReport for each SKU listed in column A of Replenishment Computation, but only for rows where Region (column E) = "NC".
- Total Inventory: Sum of OnHand, OnOrder and InTransit
- Average Sales/day: Looks up the SKU within SKUs of the Quantity sheet, retrieves the average value for the sum of the columns, meaning, Sum columnns and divide by 6 and than divide by 30. 
- Replenishment (Sales Velocity): Calculates (J206 × D206) − H206, forces it to be non-negative, and rounds it up to the nearest whole number. If the result is 0, it instead returns 1 (ensuring the output is always at least 1).
- Days of Stock: For the SKU, get days of stock from Replenishment Report.
- Replenishment (Sales Velocity): It returns the number of units to reorder: calculated as (Average Sales/Day × Days of Stock) − Current Inventory, forced to zero if negative, rounded up to the next whole number, and if that result is zero it outputs 1 instead.
- Replenish SKU: Return the SKUs where Replenishment (Sales Velocity) is greater than 0.

## Assembly Status Computation
- COlumns A to E: getProduct Name, Product SKU, Component Sku, component name and Quantity from BOM Report.
- Column F: Quantity Needed for Assembly. `=iferror(xlookup(B4,Input!A:A,Input!G:G),0)`. Return the quantity for that specific SKU from Input tab.
- Column G: Components Neddes for Assembly. Multiply Quantity Needed for Assembly by Quantity to get the total compponents quantity needed.
- Column H: it sums OnHand availability (col L) for items whose status matches the Assembly Status Computation list and are specifically located in NC - Armory.
- Column I: it sums OnOrder availability (col M) for items whose status matches the Assembly Status Computation list and are specifically located in NC - Armory.
- Column J: it sums InTransit availability (col N) for items whose status matches the Assembly Status Computation list and are specifically located in NC - Armory.
- Column K: count how many times each assembly status from column B of the Assembly Status Computation sheet appears in column B of the BOM report.
- Column L: it sums OnHand availability for items whose status matches the Assembly Status Computation list and are specifically located in NC - Main.
- Column M: it sums OnOrder availability for items whose status matches the Assembly Status Computation list and are specifically located in NC - Main.
- Column N: it sums InTransit availability for items whose status matches the Assembly Status Computation list and are specifically located in NC - Main.
- Column O: OnHend sum of NC Armory and NC Main.
- Column P: OnHand Total - Component Quantity Needed
- Column Q: Assembly Status - If OnHand Total - Component Quantity Needed is equal or lower than 0, Cannot Assemble, else, Ready for Production.
- Column R: Transfer Quantity Needed. Max between Component Quantity Needed and the sum of OnHand, OnOrder and InTransit
- Column S: Final Quantity available to Transfer. If OnHand is less than 20 and Transfer Quantity Needed is lower than OnHand, return Transfer Quantity Needed. Otherwise, 0.
- Colum T: Additional Purchases. 0 if the sum of OnHand, OnOrder and InTransit is greater than (Transfer Quantity Needed - Final Quantity available to Transfer ). Otherwise, return Transfer Quantity Needed - Final Quantity available to Transfer .


## Analysis Tab

List all SKU, Assembly Status and the Average of OnOrder from Assembly Status COmputation where the SKUs are in the Replenish SKU from Replenishment COmputation and Assembly Status is Ready for Production.
Also a column named Available in NC with the sum of Available for that SKU in Availability Report were location is NC - Main, NC - Armory or NC - FFL.
Aslo a Column with the Average Monthly Sale, from Quantity.
A column naming if it's a Component SKU from the BOM Report.


Add a bolean column named Report thar is True if the rounddown of Available in NC + Average of OnOrder is less than Average Monthly Sales.

## Input tab

A copy of Analysis tab where Report column is True. Do not include that column.
column Quantity for Assembly: If the round of Average Monthly Sales - Available in NC is less than 2, return 2. Otherwise, return the round of  Average Monthly Sales - Available in NC.

## Reports

### Report Products to Assemble

- Return from Analysis: SKU, Assembly Status, Quantity for Assembly, Available in NC and Average Monthly Sales, orered in descending order by Quantity for Assembly.


