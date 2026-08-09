# Design Decisions

## Product Normalization
- Products are normalized from noisy shipment descriptions
- Categories: 浴室水龙头, 龙头配件与零件, 淋浴底盆, 浴缸, 淋浴房与淋浴门, 花洒与淋浴系统, 淋浴背板与墙板, 浴缸与淋浴排水件, 卫浴阀门

## Hot Products Scoring
- 12-month shipment count: 55%
- Buyer coverage: 30%
- Weight (log scale): 15%

## Data Sources
- Shipment data (import records)
- Company profiles with website verification
- CRM leads and contacts module

## Paid API Policy
- ImportYeti: 100 credit budget, min 25 reserve
- All paid calls go through gateway, never from UI
- Tests use mock/fixtures only
