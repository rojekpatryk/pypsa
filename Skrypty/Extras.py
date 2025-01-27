import config as cfg
from InputData import read_input_data, read_costs, read_time_series, read_scenarios_configuration
from Plotting import *
import os

def Dunkelflaute_analysis(dirname):
    scenarios_configuration = read_scenarios_configuration()
    network_scenarios = {}
    scenarios_list = scenarios_configuration.index.tolist()
    for scenario in scenarios_list:
        n_thr_years = {}
        generators_list = scenarios_configuration.loc[scenario, 'Generators'].replace('"', '').split(', ')
        p_max_CCGT = scenarios_configuration.loc[scenario, 'p_max_CCGT']
        BASE_load_name = scenarios_configuration.loc[scenario, 'BASE_load_name']
        for year in cfg.analysis_years:
            mix, commodities, base_load, renewables, tech_sheet = read_input_data(year, BASE_load_name)
            costs = read_costs(year, tech_sheet, commodities)
            ts, ts_r = read_time_series(base_load, renewables, cfg.resolution)

            ts_p = pd.DataFrame()
            for gen_name in ['onwind', 'solar']:
                p_nom_max = mix.loc[gen_name, year]
                p_max_pu = ts[gen_name]
                ts_p[gen_name] = p_nom_max * p_max_pu
            ts_p['offshore+PV'] = ts_p['onwind'] + ts_p['solar']

            plt.figure(figsize=(15, 10))
            values, bins, bars = plt.hist(ts_p['offshore+PV'], edgecolor='white', bins=np.arange(999.999, max(ts_p['offshore+PV']) + 2, 1000))
            plt.xlabel("Offshore+PV")
            plt.ylabel("Electricity production ")
            plt.title('RES output power production distribution')
            plt.bar_label(bars, fontsize=10, color='navy')
            plt.margins(x=0.01, y=0.1)
            plt.show()


            ts_p['is zero'] = np.where(ts_p['offshore+PV'] <= 0.10 * max(ts_p['offshore+PV']), 1, 0) # TODO co traktujemy jako 0 - dunkelflaute definicja
            ones_chains_lengths = []
            current_chain_length = 0
            for x in ts_p['is zero']:
                if x == 1:
                    current_chain_length += 1
                elif current_chain_length > 0:
                    ones_chains_lengths.append(current_chain_length)
                    current_chain_length = 0
            if current_chain_length > 0:
                ones_chains_lengths.append(current_chain_length)

            plt.figure(figsize=(15, 10))
            values, bins, bars = plt.hist(pd.Series(ones_chains_lengths), edgecolor='white', bins=np.arange(0.999, max(ones_chains_lengths) + 1, 1))
            plt.xlabel("Dunkelflaute length")
            plt.ylabel("Number of occurences")
            plt.title('Dunkelflaute duration distribution (10%)')
            plt.bar_label(bars, fontsize=10, color='navy')
            plt.margins(x=0.01, y=0.1)
            plt.show()

            ones_chain_series = pd.Series(ones_chains_lengths)
            zero_hours_grouped = ones_chain_series.groupby(lambda x: ones_chain_series[x]).count()

            zero_hours_df = pd.DataFrame(zero_hours_grouped)
            zero_hours_df.reset_index(inplace=True)
            zero_hours_df['iloczyn'] = zero_hours_df['index'] * zero_hours_df[0]
            number_of_hours_Dunkelflaute = zero_hours_df.loc[zero_hours_df['index'] > 4, 'iloczyn'].sum()
            zero_hours_df.to_excel(os.path.join(dirname, 'histogram_RES_10proc.xlsx'))
            print('a')