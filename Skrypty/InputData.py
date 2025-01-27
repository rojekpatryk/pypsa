import pandas as pd
import config as cfg

#https://www.renewables.ninja/

def read_scenarios_configuration():
    inputPath = '../InputData/' + cfg.input_excel_name + '.xlsx'
    scenarios_sheet = pd.read_excel(inputPath, sheet_name='scenarios', index_col=None)

    return scenarios_sheet

def read_input_data(year, BASE_load_row_name):
    inputPath= '../InputData/' + cfg.input_excel_name + '.xlsx'

    mix = pd.read_excel(inputPath, sheet_name='mix', index_col=0) *1000 # GW to MW
    commodities = pd.read_excel(inputPath, sheet_name='commodities', index_col=0)

    renewables = pd.read_excel(inputPath, sheet_name='renewables', parse_dates=True, index_col=0)
    tech_sheet = pd.read_excel(inputPath, sheet_name='tech_sheet', index_col=0)

    yearly_load = pd.read_excel(inputPath, sheet_name='yearly load', index_col=0)
    BASE_load = yearly_load.loc[BASE_load_row_name, year]
    BASE_load_h = pd.Series(index=renewables.index, data = BASE_load)

    tech_variable = pd.read_excel(inputPath, sheet_name='tech_variable', index_col=0)


    return mix, commodities, BASE_load_h, renewables, tech_sheet, tech_variable

def calc_load(y, yearly_load, load_ts):

    total_hourly_demand_sum = load_ts['load'].sum()

    # Calculate the yearly value from the yearly load sheet
    yearly_value = yearly_load.loc['Electricity demand', y]
    # Calculate the adjustment ratio
    adjustment_ratio = yearly_value / total_hourly_demand_sum
    # Adjust the hourly energy demand
    hourly_load_y = load_ts['load'] * adjustment_ratio
    return hourly_load_y

def read_costs(year, tech_sheet, tech_variable, commodities):
    ############## Costs ################
    # url = f"https://raw.githubusercontent.com/PyPSA/technology-data/master/outputs/costs_{year}.csv" # tylko dostępne 5-latki. Pomiędzy trzeba byłoby robić np. interpolację
    #
    # costs = pd.read_csv(url, index_col=[0, 1])
    #
    # costs.loc[costs.unit.str.contains("/kW"), "value"] *= 1e3 #przeliczanie danych z bazy z kW na MW
    # costs.unit = costs.unit.str.replace("/kW", "/MW")

    defaults = {
        "FOM": 0,
        "VOM": 0,
        "efficiency": 1,
        "fuel": 0,
        "investment": 0,
        "lifetime": 25,
        "CO2 intensity": 0,
        "discount rate": 0.07,
    }
    costs = pd.DataFrame()
    # costs = costs.value.unstack().fillna(defaults)
    costs.loc['coal', 'fuel'] = commodities.loc['Coal price', year] # Aurora dla ZE PAK
    costs.loc['lignite', 'fuel'] = commodities.loc['Lignite price', year] # EY
    costs.loc['gas', 'fuel'] = commodities.loc['Gas price', year] # Aurora dla ZE PAK
    costs.loc['ENS', 'fuel'] = commodities.loc['ENS price', year] # Aurora dla ZE PAK


    # for fuel in list(tech_sheet['fuel'].dropna()):
    #     costs.loc[fuel, 'CO2 intensity'] = row_vals['CO2 intensity']

    for row_name, row_vals in tech_sheet[['fuel', 'CO2 intensity']].iterrows():
        if isinstance(row_vals['fuel'], str):
            costs.loc[row_vals['fuel'], 'CO2 intensity'] = row_vals['CO2 intensity']

    for row_name, row_vals in tech_sheet.iterrows():
        fuel = row_vals.pop('fuel')
        row_vals = row_vals.dropna()
        # if 'variable' in row_vals.values:
        for column_name, value in row_vals.items():
            if value == 'variable':
                costs.loc[row_name, column_name] = tech_variable.loc[row_name + '_' + column_name, year]
            else:
                costs.loc[row_name, column_name] = value
        # else:
        #     costs.loc[row_name, row_vals.index] = row_vals.values

        if ('battery' not in row_name) and ('ESP' not in row_name):
            costs.loc[row_name, 'fuel'] = costs.at[fuel, "fuel"]
        else:
            costs.loc[row_name, 'fuel'] = 0

    for row_name, row_vals in tech_sheet[['fuel', 'CO2 intensity']].iterrows():
        if isinstance(row_vals['fuel'], str):
            costs.loc[row_vals['fuel'], 'CO2 intensity'] = row_vals['CO2 intensity']

    def f_annuity(r, n):  #TODO GK: zmienione żeby uwzględnić stopę dyskonta 0
        if r == 0:
            return 1 / n
        else:
            return r / (1.0 - 1.0 / (1.0 + r) ** n)

    costs["marginal_cost"] = costs["VOM"] + costs["fuel"] / costs["efficiency"] + costs['CO2 intensity'] / costs["efficiency"] * commodities.loc['Carbon price', year]
    annuity = costs.apply(lambda x: f_annuity(x["discount rate"], x["lifetime"]), axis=1)
    costs["capital_cost"] = (annuity + costs["FOM"] / 100) * costs["investment"]

    return costs


def read_time_series(hourly_load_y, renewables, resolution):
    ts = pd.DataFrame(index=hourly_load_y.index)
    ts.loc[:, 'load'] = hourly_load_y # TODO load z PSE jest w local time a OZE jest z renewables.ninja w UTC. Trzeba ujednolicić, chociaż na razie load nie będzie wykorzystywany bo liczymy pasek
    ts.loc[:, 'solar'] = renewables.loc[:, 'PV'].values # TODO timestamp z 2016 wstawiony na sztywno w 2018 i coś jest nie tak że danych jest więcej niż 8760
    ts.loc[:, 'onwind'] = renewables.loc[:, 'Onshore'].values
    ts.loc[:, 'offwind'] = renewables.loc[:, 'Offshore'].values
    ts.loc[:, 'CCGT new'] = renewables.loc[:, 'CCGT new'].values

    ts[['CCGT old', 'OCGT', 'Hard Coal old', 'Hard Coal new', 'Lignite old', 'Lignite new', 'ENS']] = 1

    # TODO - jak to wpływa na magazyny? Trzeba by się trochę tym pobawić
    ts_r = ts.resample(f"{resolution}h").sum()

    return ts, ts_r