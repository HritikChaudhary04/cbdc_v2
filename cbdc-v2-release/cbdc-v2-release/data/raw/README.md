Put the raw data archives here before committing:
- campaign_data.tar.gz (all reportable testbed rounds: block-level CSVs, metrics, summaries, console logs)
- EF_results.tar.gz (validator-failure and surge rounds)
- B10C_results.tar.gz (drift check: fresh B = 10 network at 150 TPS, 3 repetitions; paper Sec. 6.2, Table tab:blocksize_tb caption)
To use them, extract each archive into a folder of the same name under data/raw/.
The full archive with raw peer and orderer logs (about 700 MB) is not included because of size; it is available from the author on request.
