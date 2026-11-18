# Datasets, labels, and graph boundaries

## Synthetic training graph

`ml.preprocessing.generate_synthetic_network` creates processed node/edge CSVs containing five entity types: SUPPLIER, MANUFACTURER, PORT, WAREHOUSE, RETAILER. The tested graph has 25 nodes and 42 directed edges.

`ml.scenarios.generate_scenarios` creates synthetic disruption propagation labels. `ml.gnn.prepare_dataset` builds the classifier training table. `ml.gnn.train_gnn` generates the GraphSAGE classification checkpoint. `ml.gnn.delay_regression --train` trains the regression model on synthetic targets.

Observed scenario evaluation: classification summary 14 NORMAL, 10 AFFECTED, 1 DISRUPTED for `PORT_001`; mean downstream delay 8.10 days, maximum 10.18 days for a 14-day synthetic source disruption.

The recorded delay regression evaluation metrics were MAE 0.357 days and RMSE 0.644 days on synthetic held-out source scenarios. These values do not quantify live-news performance.

## Separate benchmarking graph

The optional benchmark generator creates 5,000 entities and 12,000 directed edges. Use it to test Neo4j search/neighborhood response times and bounded React Flow exploration. This is not the trained GraphSAGE inference dataset.

## Raw DataCo

DataCo data can support background data analysis and ETL. Do not claim it supplies verified historical disruption outcomes for the GraphSAGE models.

## Data availability

Datasets and model checkpoints are deliberately Git-ignored (large/derived or potentially restricted). A fresh clone must execute the generation/import/training steps in `SETUP.md`. Never publish confidential company documents or third-party data without appropriate rights.
