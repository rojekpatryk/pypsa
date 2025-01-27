battery_capacity = 4
resolution = 1  # TODO zmień to na 1 do finalnych obliczeń


input_excel_name = "InputData v0.24"
custom_text_to_directory = '_alpha'

ENS_adjustment = True
ENS_adjustment_name = 'Zakup na spot'
fix_p_BESS = False
moc_p_BESS = 477+5

# analysis_years = [2030, 2031] #[2030, 2035, 2040, 2045, 2050]
# analysis_years = [2027, 2028, 2029, 2030] #[2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036, 2040, 2045, 2050] #[2030, 2035, 2040, 2045, 2050]
analysis_years = [i for i in range(2027, 2051+1)]
# analysis_years.extend([2040, 2045, 2050])

scenario_select = True
scenario_select_list = ['SYST2']


carriers = [
    "onwind",
    "offwind",
    "solar",
    "battery storage",
    "gas",
    "coal",
    "lignite"
]

disp_bool = True

gen_params = {
'CCGT old' : {'carrier': 'gas', 'p_nom_extendable':disp_bool},
'CCGT new' : {'carrier': 'gas', 'p_nom_extendable':disp_bool},
'OCGT' : {'carrier': 'gas', 'p_nom_extendable':disp_bool},
'Hard Coal old' : {'carrier': 'coal', 'p_nom_extendable':disp_bool},
'Hard Coal new' : {'carrier': 'coal', 'p_nom_extendable':disp_bool},
'Lignite old' : {'carrier': 'lignite', 'p_nom_extendable':disp_bool},
'Lignite new' : {'carrier': 'lignite', 'p_nom_extendable':disp_bool},
'onwind' : {'carrier': 'onwind', 'p_nom_extendable':True},
'offwind' : {'carrier': 'offwind', 'p_nom_extendable':True},
'solar' : {'carrier': 'solar', 'p_nom_extendable':True},
'ENS' : {'carrier': 'ENS', 'p_nom_extendable':True},
}

# Define color dictionary for technologies and order in plots
color_dict_def = {
    'solar': 'gold',
    'onwind': 'steelblue',
    'offwind': 'aqua',
    'Lignite old' : 'sienna',
    'Lignite new' : 'lightsalmon',
    'lignite' : 'sienna',
    'coal' : 'tab:gray',
    'gas' : 'tab:olive',
    'Hard Coal old': 'tab:gray',
    'Hard Coal new': 'lightgray',
    'CCGT old': 'darkolivegreen',
    'CCGT new': 'yellowgreen',
    'OCGT': 'darkred',
    'battery storage': 'darkslateblue',
    'battery inverter + %ix storage'%battery_capacity : 'darkslateblue',
    'ESP old': 'teal',
    'ESP new': 'limegreen',
    'ENS': 'darkred',
    'Zakup na spot' : 'darkred',
}


plot_names_dict = {
    'fig 1': 'Cf',
    'fig 2': 'Load',
    'fig 3': 'Optimized_dispatch',
    'fig 4': 'Marginal_and_Capital_Costs',
    'fig 5': 'Objective_function',
    'fig 6': 'Capacity_and_generation',
}

ESP_old_capital_cost = 24000-23999 #redukcja z RM