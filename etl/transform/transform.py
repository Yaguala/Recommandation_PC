import pandas as pd
import regex as re
from pathlib import Path


project_root = Path(__file__).resolve().parent.parents[0]



def concat_mac_pc():
    mac = pd.read_csv(project_root / 'data' / 'raw' / 'ldlc_pc_mac.csv')
    pc = pd.read_csv(project_root / 'data' / 'raw' / 'ldlc_pc.csv')

    #mise a jour des prix des macs
    #mac = update_price_mac(pd.read_csv('ldlc_pc_mac.csv'), pd.read_csv('mac_new_price.csv'))

    #renomage colonne url_pc
    mac = mac.rename(columns={'url_pc': 'url'})

    #concat des pc et des macs
    df = pd.concat([pc, mac])

    #suppression colonnes inutiles
    df = df.drop(columns=['AI Ready', 'Accessoires Supplémentaires', 'Disponibilité des pièces détachées', 'Personne responsable', 'Adresse postale', 'Adresse électronique', 'Définition de l\'indice'])

    #creation d'une colonne par type d'activités
    df['Type d\'activités'] = df['Type d\'activités'].astype(str).apply(lambda x : x.replace(' ', ''))
    df = pd.concat([df, df['Type d\'activités'].str.get_dummies(sep=',')], axis=1)

    #suppression colonne type d'activités
    df = df.drop(columns=['Type d\'activités'])

    #creation csv
    df.to_csv(project_root / 'data' / 'transform' / 'pc_step1.csv', index=False)


def get_cpu_reference(s):

    #si s contient M4
    if len(re.findall('M4', s)) > 0:

        #on ne garde que la reference de la puce ainsi que sont nombre de coeurs entre parenthese
        s = re.findall('Puce\sApple\s([^\(]+)\(CPU\s(\d+)', s)

        #on retourne sous la bonne forme
        return f"{s[0][0]}({s[0][1]}-Core)"
    else:

        #on recupere ce qui est entre le debut de la str et la premiere perenthese ouvrante
        s = re.findall('^([^\(]+)', s)[0]

        #On supprime Intel
        s = re.sub('Intel', '', s).strip()

        #On supprime AMD
        s = re.sub('AMD', '', s).strip()
        
        #On supprime Puce Apple
        s = re.sub('Puce Apple', '', s).strip()

        #On remplace les - par un espace
        s = re.sub('-', ' ', s).strip()
        return s

def get_gpu_reference(s):

    #si s contient Apple
    if len(re.findall('Apple', s)) > 0:

        #on supprime Apple
        s = re.sub('Apple', '', s)

        #on supprime espacecoeurs par -core
        s = re.sub('\scoeurs', '-core)', s)

        #On split la str en deux ) GPU
        s = s.split('GPU')

        #On retourne sous le bon format
        return f"{s[0].strip()} GPU ({s[1].strip()}"
    else:

        #On supprime NVIDIA
        s = re.sub('NVIDIA', '', s).strip()

        #On supprime AMD
        s = re.sub('AMD', '', s).strip()

        #On supprime GeForce
        s = re.sub('GeForce', '', s).strip()

        return s

def clean_cpu(s):

    #On supprime Apple+espace
    s = re.sub('(Apple\s)', '' , s)

    #Si s contient Snapdragon
    if len(re.findall('Snapdragon', s)) > 0:

        #On supprime lese parentheses
        s = re.sub('[\(\)]', '', s)

        #On remplace des - par espace
        s = re.sub('-', ' ', s)
    return s


def clean_gpu(s):

    #On remplace Core par core
    s = re.sub('Core', 'core' , s).strip()

    #On supprime Laptop
    s = re.sub('Laptop', '', s).strip()

    #On supprime Mobole
    s = re.sub('Mobile', '', s).strip()
    return s


def add_cpu_scores(df_name):

    #Load pc
    pc = pd.read_csv(df_name)

    #Drop rows with nan in Type de processeur
    pc = pc.dropna(subset=['Type de processeur'])
    
    #Create new column with the name of the CPU
    pc['reference CPU'] = pc['Type de processeur'].apply(get_cpu_reference)

    #Load cpu benchmarks
    score_cpu = pd.read_csv(project_root / 'data' / 'processed' /'cpu_benchmarks.csv')
    
    #Change columns name
    score_cpu = score_cpu.rename(columns={'name': 'reference CPU', 'single-core': 'CPU_benchmark_single_core', 'multi-core': 'CPU_benchmark_multi_core'})

    #Clean score_cpu
    score_cpu['reference CPU'] = score_cpu['reference CPU'].apply(clean_cpu)

    #merge pc and score_cpu
    pc = pd.merge(pc, score_cpu, on='reference CPU')

    return pc


def add_gpu_scores(df_name):
    #Load pc
    pc = pd.read_csv(df_name)

    #Load cpu benchmarks
    score_gpu = pd.read_csv(project_root / 'data' / 'processed' / 'gpu_benchmarks.csv')

    #Supprimer les lignes qui ont chipset graphique nan
    pc = pc.dropna(subset='Chipset graphique')
    print(pc.shape)

    #Creation nouvelle colonne reference GPU
    pc['reference GPU'] = pc['Chipset graphique'].apply(get_gpu_reference)

    #Change columns name
    score_gpu = score_gpu.rename(columns={'name': 'reference GPU'})
    
    #Clean score_gpu
    score_gpu['reference GPU'] = score_gpu['reference GPU'].apply(clean_gpu)

    #merge pc and score_cpu
    pc = pd.merge(pc, score_gpu, how='left', on='reference GPU')

    return pc


def real_price(df_name):
    df = pd.read_csv(df_name)

    #creation d'une colonne qui contient le price sous forme de float
    df['price_float'] = df['price'].apply(lambda x : re.findall('\*([^$]+$)', x)[0] if len(re.findall('\*([^$]+$)', x)) else x )
    df['price_float'] = df['price_float'].apply(lambda x : float(''.join(re.findall('([\d]+)', x))) / 100)

    #mise au propre de la colonne price
    df['price'] = df['price_float'].apply(lambda x : str(x).replace('.', '€'))
    df['price'] = df['price'].apply(lambda x : x if len(re.findall('€([\d]+)', x)[0]) == 2 else x + '0')

    #creation colonne du nombre de point CPU par euros
    df['CPU_multi_core_points_by_euros'] = df['CPU_benchmark_multi_core'] / df['price_float']

    #On remplace les valeurs 3d_mark et geekbench nulles ou egal a '-' par 1 (si manquant c'est que le score n'est pas pertinent)
    df['3d_mark'] = df['3d_mark'].fillna(1)
    df['3d_mark'] = df['3d_mark'].replace(['-'], 1)
    df['geekbench'] = df['geekbench'].fillna(1)
    df['geekbench'] = df['geekbench'].replace(['-'], 1)

    #creation colonne du nombre de point 3d_mark GPU par euros
    df['3d_mark_points_by_euros'] = df['3d_mark'].astype(float) / df['price_float']
    
    #creation colonne du nombre de point geekbench GPU par euros
    df['geekbench_points_by_euros'] = df['geekbench'].astype(float) / df['price_float']
    
    #creation colonne du nombre de point 3d_mark GPU + CPU par euros
    df['3d_mark_and_CPU_points_by_euros'] = (df['3d_mark'].astype(float) + df['CPU_benchmark_multi_core']) / df['price_float']
    
    #creation colonne du nombre de point geekbench GPU + CPU par euros
    df['geekbench_and_CPU_points_by_euros'] = (df['geekbench'].astype(float) + df['CPU_benchmark_multi_core']) / df['price_float']

    return df


def real_price_v2(df_name):
    df = pd.read_csv(df_name)

    #creation d'une colonne qui contient le price sous forme de float
    df['price_float'] = df['price'].apply(lambda x : re.findall('\*([^$]+$)', x)[0] if len(re.findall('\*([^$]+$)', x)) else x )
    df['price_float'] = df['price_float'].apply(lambda x : float(''.join(re.findall('([\d]+)', x))) / 100)

    #mise au propre de la colonne price
    df['price'] = df['price_float'].apply(lambda x : str(x).replace('.', '€'))
    df['price'] = df['price'].apply(lambda x : x if len(re.findall('€([\d]+)', x)[0]) == 2 else x + '0')

    return df


def score_by_euro(df):

    #creation colonne du nombre de point CPU par euros
    df['CPU_multi_core_score_by_euro'] = df['CPU_benchmark_multi_core'] / df['price_float']

    #On remplace les valeurs 3d_mark et geekbench nulles ou egal a '-' par 1 (si manquant c'est que le score n'est pas pertinent)
    df['3d_mark'] = df['3d_mark'].fillna(1)
    df['3d_mark'] = df['3d_mark'].replace(['-'], 1)
    df['geekbench'] = df['geekbench'].fillna(1)
    df['geekbench'] = df['geekbench'].replace(['-'], 1)

    df['GPU_CPU_score_by_euro'] = ((df['3d_mark'].astype(float) + df['geekbench'].astype(float)) / 2) / df['price_float']

    df['GPU_CPU_score'] = (df['3d_mark'].astype(float) + df['geekbench'].astype(float)) / 2


    return df


def update_price_mac(df1, df2):

    #renommage de la colonne price avant merge
    df2 = df2.rename(columns={'price': 'new_price'})

    #merge du df mac contenant des prix par mois et du df contentant les prix fixes
    df1 = df1.merge(df2, how='left', on='url_pc')

    #Si il y une valeur dans new_price, on la met dans price
    df1['price'] = df1[['price', 'new_price']].apply(lambda x : x['new_price'] if isinstance(x['new_price'], float) is False else x['price'], axis=1)

    #On supprime la colonne new_price
    df1 = df1.drop(columns=['new_price'])

    return df1


#def reco_pc_by_budget(df_name, price, gpu=False):
#    
#    df = pd.read_csv(df_name)
#
#
#    df = df[df['price_float'] < float(price)]
#    if gpu:
#        df = df.sort_values(by=['GPU_CPU_score'], ascending=False)
#        #df = df.sort_values(by=['GPU_CPU_score_by_euro'], ascending=False)
#    else:
#        df = df.sort_values(by=['CPU_benchmark_multi_core'], ascending=False)
#        #df = df.sort_values(by=['CPU_multi_core_score_by_euro'], ascending=False)
#
#    print(df[['price', 'CPU_benchmark_multi_core', 'GPU_CPU_score', 'url']])
#    #print(df[['price', 'CPU_multi_core_score_by_euro', 'GPU_CPU_score_by_euro', 'url']])


def main():
    concat_mac_pc()
    add_cpu_scores(project_root / 'data' / 'transform' /'pc_step1.csv').to_csv(project_root / 'data' / 'transform' /'pc_step2.csv', index=False)
    add_gpu_scores(project_root / 'data' / 'transform' /'pc_step2.csv').to_csv(project_root / 'data' / 'transform' /'pc_step3.csv', index=False)
    score_by_euro(real_price_v2(project_root / 'data' / 'transform' /'pc_step3.csv')).to_csv(project_root / 'data' / 'transform' /'pc_step4.csv', index=False)
#    reco_pc_by_budget('pc_step4.csv', 1500)
#    reco_pc_by_budget('pc_step4.csv', 1500, gpu=True)


if __name__ == '__main__':
    main()