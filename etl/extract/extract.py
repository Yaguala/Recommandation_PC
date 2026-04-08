
from pathlib import Path
from tqdm import tqdm
from bs4 import BeautifulSoup as bs
import requests as r
import pandas as pd
import cloudscraper
import time
import random
import regex as re

tqdm.pandas()  # Enable tqdm with pandas



############### Basic Tables ##################


project_root = Path(__file__).resolve().parent.parents[0]

def get_text_from_url(url):
    scraper = cloudscraper.create_scraper(
        browser={'browser':'firefox','platform':'windows','desktop':True}
    )
    response = scraper.get(
        url=url,
        timeout=15
    )
    print(response.status_code)
    if response.status_code == 200:
        return response.text
        # traiter le HTML...
    else:
        print('Erreur', response.status_code)


def get_all_pc_url(url):
    '''Retourne un DataFrame contenant les noms et URL des laptops du site web LDLC'''

    #Definition des variables
    url_pc_list = []
    name_list = []
    page_number = ''

    #Trouver le numero de la derniere page
    soup = bs(get_text_from_url(url), features="lxml")
    pagination = soup.find('ul', attrs={'class' : 'pagination'})
    last_page = pagination.find_all('a')[-2].text

    #Loop sur toutes les pages
    for page in range(0, int(last_page) - 1):

        #Soupe sur la current page
        soup = bs(get_text_from_url(url+page_number), features="lxml")

        #On recherche la section (le champs des lignes) des pc
        pc_section = soup.find('div', attrs={'class' : 'listing-product'})

        #On recupere toutes les lignes des pc
        all_pc = pc_section.find_all('li', attrs={'class' : 'pdt-item'})

        #On loop sur les lignes des pc
        for pc in all_pc:
            try:
                #on recupere le nom du pc
                name = pc.find('h3', attrs={'class' : 'title-3'}).text.strip()

                #On recupere l'URL du pc
                url_pc = 'https://www.ldlc.com' + re.findall('<a href="([^"]+">)', str(pc.find('a')))[0]

                #On ajoute les noms et URL dans les listes respectives
                name_list.append(name)
                url_pc_list.append(url_pc)

            #Si error imprimer message
            except Exception as e:
                print(f"Error, {e}")
        #On met a jour le nom de la prochaine page
        page_number = f"page{page + 2}/"

    #On return un DataFrame contenant les listes
    return(pd.DataFrame({'name': name_list, 'url_pc' : url_pc_list}))
            

def main():
    get_all_pc_url('https://www.ldlc.com/informatique/ordinateur-portable/pc-portable/c4265/').to_csv(project_root / 'data' / 'basictable' / 'url_and_name_all_pc.csv', index=False)
    get_all_pc_url('https://www.ldlc.com/informatique/ordinateur-portable/portable-mac/c4266/').to_csv(project_root / 'data' / 'basictable' / 'url_and_name_all_mac.csv', index=False)

if __name__ == '__main__':
    main()


########################################################



def get_text_from_url(url):
    scraper = cloudscraper.create_scraper(
        browser={'browser':'chrome','platform':'windows','desktop':True}
    )
    response = scraper.get(
        url=url,
        timeout=15
    )
    # print(response.status_code) # Reponse checker
    if response.status_code == 200:
        return bs(response.text)
        # traiter le HTML...
    else:
        print('Erreur', response.status_code)



def get_details(url):
    # Adding a timmer
    time.sleep(random.uniform(5, 6))

    data = get_text_from_url(url)
    try:
        img = data.find_all("a", {"class" : "pVignette photo"})[0]['href']

        # Price selection over multiple prices offers if len is lower then 20 we save it else we try a second value otherwise we save it.
        for i in range(0,len(data.find_all("div", {"class" : "price"}))):
            sg_price = data.find_all("div", {"class" : "price"})[i].text
            if len(sg_price) < 20 :
                price = sg_price
            else:
                price = sg_price

        # Step 1: Create an empty dictionary
        dic_caracteristiques = {}

        # Step 2: Get all the <td> elements with class "checkbox" and "no-checkbox"
        td_elements = data.find_all("td", {"class": ["checkbox", "no-checkbox"]})
        td_caracteristiques = data.find_all("td", {"class": "label"})


        # Step 3: Loop over both the keys and the <td> elements using a for loop
        row = -1 # Counter for the lines of details elements
        for i in range(len(td_caracteristiques)):
            row+=1  # Counter for the lines of details elements
        
            key = td_caracteristiques[i].text.strip("\n")     # Get the name of the characteristic
            rowspan = td_caracteristiques[i].get("rowspan")   # Get if existe the rowspan value! Otherwise gets a None

            if rowspan is not None and int(rowspan) > 1: # Verifies if rowspan is bigger the 1 to proced to a repetitive loop over the same caracteristique
                if "checkbox" in td_elements[row].get("class", []): # Check if is a "checkbox" other with all text is in the same line
                    #print(rowspan)
                    valuelist = []
                    for x in range(int(rowspan)):
                        #print(td_elements[row+x].text.strip())
                        valuelist.append(td_elements[row+x].text.strip())         # Get the text inside the <td> element and remove extra spaces
                                                                                # Add x value to the row so he repites the element line
                    value = ", ".join(valuelist)
                    dic_caracteristiques[key] = value
                    row += (int(rowspan)-1) # Adds the rowspan number of lines to match the caracteristique "number of lines"
                else:
                    value = td_elements[row].text.strip()
                    dic_caracteristiques[key] = value # Add it to the dictionary
                                            
            else:
                value = td_elements[row].text.strip()
                dic_caracteristiques[key] = value   # Add it to the dictionary
        
        dic_caracteristiques["img_url"] = img
        dic_caracteristiques["price"] = price
        return dic_caracteristiques
    except Exception as e:
        #print(f"Error, {e}")
        return print(f"Error, {e}")
    

# Get the project root (assumes this script is inside etl/extract/)
project_root = Path(__file__).resolve().parent.parents[0]


# Build the correct path to the CSV (project_root / "ulr_and_name_all_pc.csv")
# Load the CSV
df_ldlc = pd.read_csv(project_root / 'data' / 'basictable' / "url_and_name_all_pc.csv")
df_ldlc['url_pc'] = df_ldlc['url_pc'].str.replace('">', '')




# Now use .progress_apply instead of .apply
df_details = df_ldlc['url_pc'].progress_apply(get_details).apply(pd.Series)

df_pcs = pd.concat([df_ldlc, df_details], axis=1)


df_pcs.to_csv(project_root / 'data' / 'raw' / "ldlc_pc.csv", index=False)



############################## MACS ####################################

df_macs = pd.read_csv(project_root / 'data' / 'basictable' / 'url_and_name_all_mac.csv')

df_macs['url_pc'] = df_macs['url_pc'].str.replace('">', '')


# Now use .progress_apply instead of .apply
df_details_macs = df_macs['url_pc'].progress_apply(get_details).apply(pd.Series)


df_macs_concat = pd.concat([df_macs, df_details_macs], axis=1)


df_macs_concat.to_csv(project_root / 'data' / 'raw' / "ldlc_pc_mac.csv", index=False)



########################### Bench Marks ####################################


def get_text_from_url(url):
    scraper = cloudscraper.create_scraper(
        browser={'browser':'firefox','platform':'windows','desktop':True}
    )
    response = scraper.get(
        url=url,
        timeout=15
    )
    print(response.status_code)
    if response.status_code == 200:
        return response.text
        # traiter le HTML...
    else:
        print('Erreur', response.status_code)

def scrap_specs_create_csv(url, csv_name, indexes:list, columns_name:list):
    print(url)
    soup = bs(get_text_from_url(url), features="lxml")
    table = soup.find('table', attrs={'class': 'table-list sortable'})
    all_lines = table.find_all('tr')
    datas = {'name' : []}
    for name in columns_name:
        datas[name] = []
    for line in all_lines:
        try:
            tds = line.find_all('td')
            datas['name'].append(tds[1].find('a').text.strip())
            for name,index in zip(columns_name, indexes):
                datas[name].append(tds[index].find('div', attrs={'style' : 'margin-bottom: 6px;'}).text.strip())
        except Exception as e:
            print(f"Error, {e}")
    pd.DataFrame(datas).to_csv(project_root / 'data' / 'processed' / csv_name, index=False)



def main():
    scrap_specs_create_csv('https://nanoreview.net/en/cpu-list/laptop-chips-rating', 'cpu_benchmarks.csv', [6,7], ['single-core', 'multi-core'])
    scrap_specs_create_csv('https://nanoreview.net/en/gpu-list/laptop-graphics-rating', 'gpu_benchmarks.csv', [7,8], ['geekbench', '3d_mark'])


if __name__ == '__main__':
    main()