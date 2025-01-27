import matplotlib.pyplot as plt
import pandas as pd
import config as cfg
import pypsa
from Plotting import *
from InputData import read_input_data, read_costs, read_time_series, read_scenarios_configuration
import os
import datetime
import concurrent.futures
import warnings

from Skrypty.Output import ModelResults

warnings.filterwarnings("ignore", category=DeprecationWarning)

# TODO GK
# Plotting, w58 sprawdzić warunek na charge bo wywala warning że do inputu dajemy te same wartości

#TODOS
# Sprawdzić HHV/LHV czy są ok (sprawności, ceny paliw, emisje)
# ENS: Dać slack variable na generację wiatrową albo lepiej zrozumieć co wymusza wiatr, zrobić prosty scenariusz z samym wiatrem plus PV i ENS
# Zrobić  zapisywanie do excela
# Uwzględniamy jakoś inflację? (W costs nie przerobionych jest rok bazowy)
# Nie mamy ramps, startup costs etc - chyba nie bedziemy mieli bo trzeba by miec pojedyncze jednostki - moze do sciagniecia z pypsa albo instrat

# Nowe todos:
# CFy
# LCOE
# Research na dane wsadowe
# A dodatkowe przychody z nadwyżek OZE ponad BASE jakoś liczmy?
# Wiadomo, że maksymalna moc OZE jaką wykorzystamy to BASE + moc magazynu, będą godziny, kiedy na pasek idzie 100% OZE i będą kiedy idzie 20%
# Generalnie mamy 100% mocy z każdej technologii w systemie, żeby stworzyć pasek o mocy ok 25% zapotrzebowania
# zapotrzebowanie na BASE rosnie rok po roku bo zapotrzebowanie rosnie, ale możliwość jego dostarczania będzie coraz trudniejsza



def gen_scenarios_w_years(scenarios_configuration, years):
    scenarios_years_configuration = pd.DataFrame()
    for year in years:
        df = pd.DataFrame()
        df = scenarios_configuration
        if cfg.scenario_select == True:
            df = df[df['Scenario'].isin(cfg.scenario_select_list)].copy()
        df['year'] = year
        scenarios_years_configuration = pd.concat([scenarios_years_configuration, df])
    col_years = scenarios_years_configuration.pop('year')
    scenarios_years_configuration.insert(0, 'year', col_years)
    # scenarios_years_configuration.reset_index()
    scenarios_years_configuration.set_index(scenarios_years_configuration['year'].astype(str) + '_' + scenarios_years_configuration['Scenario'], inplace=True)
    return scenarios_years_configuration

def run_pypsa_case(params):
    generators_list = params.at['Generators'].replace('"', '').split(', ')
    p_max_CCGT = params.at['p_max_CCGT']
    p_max_BESS = params.at['Moc_BESS']
    BASE_load_name = params.at['BASE_load_name']
    year = params.at['year']
    # print('\n--------------OPTYMALIZACJA Scenariusz: ', params.at['scenario'], ', Rok: ', params.at['year'], ' ------------------------------')
    # print('-------------------------- Czas obliczeń: ', datetime.datetime.now() - start_time, ' ---------------------------\n')
    mix, commodities, base_load, renewables, tech_sheet, tech_variable = read_input_data(year, BASE_load_name)
    costs = read_costs(year, tech_sheet, tech_variable, commodities)

    # print('resolution ustawione na: %i' % cfg.resolution)
    ts, ts_r = read_time_series(base_load, renewables, cfg.resolution)

    ############# Model ####################
    n = pypsa.Network()
    n.add("Bus", "electricity")
    n.set_snapshots(ts.index)
    n.snapshot_weightings.loc[:, :] = cfg.resolution

    n.add(
        "Carrier",
        cfg.carriers,
        color=["dodgerblue", "aquamarine", "gold", "magenta", "orange", "dimgrey", 'sienna'],
        co2_emissions=[costs.at[c, "CO2 intensity"] for c in cfg.carriers],
    )

    n.add(
        "Load",
        "demand",
        bus="electricity",
        p_set=ts['load'],
    )

    for gen_name in generators_list:  # for gen_name, gen_params in cfg.gen_params.items():
        n.add(
            "Generator",
            gen_name,
            bus="electricity",
            carrier=cfg.gen_params[gen_name]['carrier'],
            capital_cost=costs.at[gen_name, "capital_cost"],
            marginal_cost=costs.at[gen_name, "marginal_cost"],
            efficiency=costs.at[gen_name, "efficiency"],
            p_nom_extendable=cfg.gen_params[gen_name]['p_nom_extendable'],
            p_nom_max=mix.loc[gen_name, year] if (p_max_CCGT == "mix" or gen_name != 'CCGT old') else int(p_max_CCGT),
            p_nom=0,
            p_max_pu=ts[gen_name],
        )

    n.add(
        "StorageUnit",
        "battery storage",
        bus="electricity",
        carrier="battery storage",
        max_hours=cfg.battery_capacity,
        capital_cost=costs.at["battery inverter", "capital_cost"]
                     + cfg.battery_capacity * costs.at["battery storage", "capital_cost"],
        efficiency_store=costs.at["battery inverter", "efficiency"] ** 0.5,
        efficiency_dispatch=costs.at["battery inverter", "efficiency"] ** 0.5,

        p_nom_extendable=False if cfg.fix_p_BESS else True,
        cyclic_state_of_charge=True,
        p_nom_max=None if cfg.fix_p_BESS else (mix.loc["battery storage", year] if p_max_BESS == 'mix' else p_max_BESS),
        p_nom=cfg.moc_p_BESS if cfg.fix_p_BESS else False,

        # state_of_charge_initial_per_period = True,
        # state_of_charge_initial = 1000000000,

    )

    if params.loc['ESP_enable'] == 1:
        n.add(
            "StorageUnit",
            "ESP old",
            bus="electricity",
            carrier="battery storage",
            max_hours=cfg.battery_capacity,
            capital_cost=cfg.ESP_old_capital_cost,
            efficiency_store=costs.at["ESP old", "efficiency"] ** 0.5,
            efficiency_dispatch=costs.at["ESP old", "efficiency"] ** 0.5,
            p_nom_extendable=True,  # TODO: upewnić się
            cyclic_state_of_charge=True,
            p_nom_max=mix.loc["ESP old", year],
            p_nom=False,
        )

        n.add(
            "StorageUnit",
            "ESP new",
            bus="electricity",
            carrier="battery storage",
            max_hours=cfg.battery_capacity,
            capital_cost=costs.at["ESP new", "capital_cost"],
            efficiency_store=costs.at["ESP new", "efficiency"] ** 0.5,
            efficiency_dispatch=costs.at["ESP new", "efficiency"] ** 0.5,
            p_nom_extendable=True,
            cyclic_state_of_charge=True,
            p_nom_max=mix.loc["ESP new", year],
            p_nom=False,
        )


    if ("ENS" in generators_list) or ("CCGT old" in generators_list) or ("CCGT new" in generators_list):
        m = n.optimize.create_model()
        if "ENS" in generators_list:
            ens_generation = m.variables["Generator-p"].sum("snapshot").loc["ENS"].sum()
            total_demand = n.loads_t.p_set.sum().sum()
            constraint_expression = params.loc['ENS_proc'] * total_demand >= ens_generation
            m.add_constraints(constraint_expression, name="ENS-maximum_generation_share")
        if "CCGT old" in generators_list:
            CCGT_old_generation = m.variables["Generator-p"].sum("snapshot").loc["CCGT old"].sum()
            if False:
                constraint_expression2 = CCGT_old_generation <= mix.loc['CCGT old', year] * 8760 * 0.8
            else:
                CCGT_old_p_nom_opt = m.variables["Generator-p_nom"].loc["CCGT old"]
                constraint_expression2 = CCGT_old_generation <= CCGT_old_p_nom_opt * ts['CCGT old'].sum() * 0.8
            m.add_constraints(constraint_expression2, name="CCGT old-maximum_CF")
        if "CCGT new" in generators_list:
            CCGT_new_generation = m.variables["Generator-p"].sum("snapshot").loc["CCGT new"].sum()
            if False:
                constraint_expression3 = CCGT_new_generation <= mix.loc['CCGT new', year] * ts['CCGT new'].sum() * 0.33
            else:
                # CCGT_new_p_nom_opt = m.variables.Generator_p_nom.data.at["CCGT new", "solution"]
                CCGT_new_p_nom_opt = m.variables["Generator-p_nom"].loc["CCGT new"]
                constraint_expression3 = CCGT_new_generation <= CCGT_new_p_nom_opt * ts['CCGT new'].sum() * 0.33
            m.add_constraints(constraint_expression3, name="CCGT new-maximum_CF")
        n.optimize.solve_model(solver_name="highs")
    else:
        n.optimize(solver_name="highs")

    print('Year results %i' % year)

    if hasattr(n, 'objective'):
        print('\nObjective value:')
        print(n.objective / 1e9)
        # print((n.statistics.capex() + n.statistics.opex()).div(1e9))

        print('\nOptimal capacities:')
        print(n.generators.p_nom_opt.div(1e3))
        print('\nOptimal generation:')
        print(n.snapshot_weightings.generators @ n.generators_t.p.div(
            1e6))  # produkcja energii w TWh, @ robi dot product między wektorem wag a macierzą punktów pracy
    else:
        print("Brak wyniku!!!")
    return n

def run_all_cases(df):
    results_dict = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_case = {executor.submit(run_pypsa_case, row): index for index, row in df.iterrows()}
        for future in concurrent.futures.as_completed(future_to_case):
            case_index = future_to_case[future]
            try:
                result = future.result()
                results_dict[case_index] = result
            except Exception as exc:
                print(f'Case {case_index} generated an exception: {exc}')

    return results_dict



print("calculation start: ", datetime.datetime.now())
start_time = datetime.datetime.now()
date = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
dirname = os.path.join("..", "Wyniki", date + " " + cfg.input_excel_name.split(" ")[-1] + cfg.custom_text_to_directory)
os.mkdir(dirname)

scenarios_configuration = read_scenarios_configuration()
scenarios_years_configuration = gen_scenarios_w_years(scenarios_configuration, cfg.analysis_years)
n = run_pypsa_case(scenarios_years_configuration.iloc[0,:]) #TODO techniczna wklejka robocze
network_scenarios = run_all_cases(scenarios_years_configuration)

number_cases = scenarios_years_configuration.shape[0]
seconds = (datetime.datetime.now() - start_time).total_seconds()
rate = (datetime.datetime.now() - start_time).total_seconds() / scenarios_years_configuration.shape[0]
text_stats = f'liczba przypadków: {number_cases}\n czas: {seconds:.2f} sekund \n prędkość: {rate:.2f} s/przypadek\n'
print(text_stats)
with open(os.path.join(dirname, "calculation_stats.txt"), "w") as f:
    f.write(text_stats)

mr = ModelResults(dirname=dirname, network_scenarios=network_scenarios)

print('Simulation complete')