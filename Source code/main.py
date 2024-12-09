"""
Par John Jaccard
First release: 09.12.24
C'est une app qui va permettre de dl et upload des sauvegarde de jeu sur un serveur FTP distant (à faire soi-même je vais pas filer le mien).
"""
import os
import subprocess
import tkinter as tk
from tkinter import messagebox, PhotoImage,filedialog
from yaml import safe_load,safe_dump
import paramiko
from PIL import Image, ImageTk
import zipfile


# Chargement de la configuration YAML
def load_config(config_path="games.yml"):
    with open(config_path, "r") as file:
        return safe_load(file)


# Téléchargement depuis le serveur et décompression
def download_save(game, server_config):
    local_path = game['save_path']
    zip_file_path = f"{local_path}.zip"
    remote_path = f"/home/ftpuser/ftp/saves/{game['name'].replace(' ', '_')}.zip"
    try:
        # Création du dossier local si nécessaire
        os.makedirs(local_path, exist_ok=True)
        
        with paramiko.Transport((server_config['hostname'], server_config['port'])) as transport:
            transport.connect(username=server_config['username'], password=server_config['password'])
            sftp = paramiko.SFTPClient.from_transport(transport)

            # Téléchargement du fichier ZIP depuis le serveur
            sftp.get(remote_path, zip_file_path)

            # Décompression de l'archive téléchargée
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(local_path)

            # Supprimer le fichier ZIP après extraction
            os.remove(zip_file_path)

            messagebox.showinfo("Succès", f"Sauvegarde téléchargée et décompressée pour {game['name']}")

    except Exception as e:
        messagebox.showerror("Erreur", f"Échec du téléchargement ou de la décompression : {e}")


# Fonction de compression en ZIP (incluant les dossiers vides)
def zip_folder(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

            # Ajouter les dossiers vides
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                arcname = os.path.relpath(dir_path, folder_path)
                if not any(os.scandir(dir_path)):  # Vérifie si le dossier est vide
                    zipf.write(dir_path, arcname)


# Upload vers le serveur et compression avant l'upload
def upload_save(game, server_config):
    local_path = game['save_path']
    zip_file_path = f"{local_path}.zip"
    remote_path = f"/home/ftpuser/ftp/saves/{game['name'].replace(' ', '_')}.zip"
    
    try:
        # Vérification du chemin local
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Le dossier {local_path} n'existe pas.")
        
        # Compression en fichier zip
        zip_folder(local_path, zip_file_path)

        # Vérification que le fichier zip a bien été créé
        if not os.path.isfile(zip_file_path):
            raise FileNotFoundError(f"Le fichier zip {zip_file_path} n'a pas été créé.")

        # Connexion au serveur SFTP
        with paramiko.Transport((server_config['hostname'], server_config['port'])) as transport:
            transport.connect(username=server_config['username'], password=server_config['password'])
            sftp = paramiko.SFTPClient.from_transport(transport)

            # Vérification et création du répertoire 'saves' si nécessaire
            try:
                sftp.chdir('saves')  # Vérifie si le répertoire 'saves' existe
            except IOError:
                sftp.mkdir('saves')  # Crée le répertoire relatif 'saves'

            # Procéder à l'upload
            sftp.put(zip_file_path, remote_path)
            messagebox.showinfo("Succès", f"Sauvegarde uploadée pour {game['name']}")

    except FileNotFoundError as fnf_error:
        messagebox.showerror("Erreur de fichier", str(fnf_error))
    except paramiko.SSHException:
        messagebox.showerror("Erreur de connexion", "Échec de la connexion au serveur SFTP.")
    except Exception as e:
        messagebox.showerror("Erreur", f"Échec de l'upload : {e}")
    finally:
        # Suppression du fichier ZIP après upload
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)

        # Fermeture de la connexion SFTP
        try:
            sftp.close()
        except:
            pass

# Lancement du jeu
def launch_game(game):
    try:
        subprocess.Popen([game['exe_path']], cwd=os.path.dirname(game['exe_path']))
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible de lancer le jeu : {e}")

def update_game_info(game, config_path, updated_data):
    """
    Met à jour les informations d'un jeu dans le fichier YAML.
    """
    try:
        with open(config_path, 'r') as file:
            config = safe_load(file)

        for g in config['games']:
            if g['name'] == game['name']:  # Identifier le jeu à mettre à jour
                g.update(updated_data)

        with open(config_path, 'w') as file:
            safe_dump(config, file)

    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible de mettre à jour le fichier : {e}")




def update_ftp_config(config_path, updated_ftp_data):
    """
    Met à jour les paramètres FTP dans le fichier YAML.
    """
    try:
        with open(config_path, 'r') as file:
            config = safe_load(file)

        config['server'].update(updated_ftp_data)

        with open(config_path, 'w') as file:
            safe_dump(config, file)
            
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible de mettre à jour les paramètres FTP : {e}")


def edit_ftp_config_info(config_path, root):
    """
    Ouvre une fenêtre pour modifier les paramètres FTP en récupérant les valeurs du fichier YAML.
    """
    ftp_window = tk.Toplevel()
    ftp_window.title("Modifier Paramètres FTP")
    ftp_window.geometry("400x300")

    # Charger les paramètres FTP existants depuis le fichier YAML
    with open(config_path, 'r') as file:
        config = safe_load(file)

    ftp_config = config.get('server', {})

    # Champs pour les informations FTP, remplis avec les valeurs actuelles
    tk.Label(ftp_window, text="Serveur FTP :").pack(pady=5)
    entry_hostname = tk.Entry(ftp_window, width=50)
    entry_hostname.insert(0, ftp_config.get('hostname', ''))
    entry_hostname.pack()

    tk.Label(ftp_window, text="Nom d'utilisateur :").pack(pady=5)
    entry_username = tk.Entry(ftp_window, width=50)
    entry_username.insert(0, ftp_config.get('username', ''))
    entry_username.pack()

    tk.Label(ftp_window, text="Mot de passe :").pack(pady=5)
    entry_password = tk.Entry(ftp_window, width=50)
    entry_password.insert(0, ftp_config.get('password', ''))
    entry_password.pack()

    # Nouveau champ pour le port
    tk.Label(ftp_window, text="Port :").pack(pady=5)
    entry_port = tk.Entry(ftp_window, width=50)
    entry_port.insert(0, str(ftp_config.get('port', 65500)))  # Valeur par défaut = 65500
    entry_port.pack()

    # Bouton de sauvegarde des modifications
    def save_ftp_changes():
        updated_ftp_data = {
            'hostname': entry_hostname.get(),
            'username': entry_username.get(),
            'password': entry_password.get(),
            'port': int(entry_port.get())  # Sauvegarder le port comme un entier
        }
        update_ftp_config(config_path, updated_ftp_data)
        ftp_window.destroy()
        root.destroy()  # Fermer la fenêtre principale
        config = load_config(config_path)  # Recharger la configuration mise à jour
        create_ui(config, config_path)  # Relancer l'interface avec la nouvelle configuration

    tk.Button(ftp_window, text="Enregistrer", command=save_ftp_changes).pack(pady=10)



def edit_game_info(game, config_path, root):
    """
    Ouvre une fenêtre pour modifier les informations d'un jeu avec des boutons pour choisir des chemins via l'explorateur.
    """
    edit_window = tk.Toplevel()
    edit_window.title(f"Modifier {game['name']}")
    edit_window.geometry("500x200")

    # Assurer que la fenêtre d'édition reste au-dessus de la fenêtre principale
    edit_window.attributes('-topmost', True)

    # Champs pour les informations
    tk.Label(edit_window, text="Nom :").grid(row=0, column=0, padx=10, pady=5, sticky="w")
    entry_name = tk.Entry(edit_window, width=40)
    entry_name.insert(0, game['name'])
    entry_name.grid(row=0, column=1, padx=10, pady=5)

    # Fonction pour ouvrir l'explorateur et sélectionner un fichier
    def select_file(entry_widget, filetypes):
        file_path = filedialog.askopenfilename(filetypes=filetypes)
        if file_path:  # Si l'utilisateur a sélectionné un fichier
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, file_path)

    # Fonction pour ouvrir l'explorateur et sélectionner un répertoire
    def select_directory(entry_widget):
        folder_path = filedialog.askdirectory()
        if folder_path:  # Si l'utilisateur a sélectionné un dossier
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, folder_path)

    # Chemin de l'exécutable
    tk.Label(edit_window, text="Chemin de l'exécutable :").grid(row=1, column=0, padx=10, pady=5, sticky="w")
    entry_exec_path = tk.Entry(edit_window, width=40)
    entry_exec_path.insert(0, game['exe_path'])
    entry_exec_path.grid(row=1, column=1, padx=10, pady=5)
    tk.Button(edit_window, text="Choisir", command=lambda: select_file(entry_exec_path, [("Executables", "*.exe")])).grid(row=1, column=2, padx=10, pady=5)

    # Chemin de la sauvegarde
    tk.Label(edit_window, text="Chemin de la sauvegarde :").grid(row=2, column=0, padx=10, pady=5, sticky="w")
    entry_save_path = tk.Entry(edit_window, width=40)
    entry_save_path.insert(0, game['save_path'])
    entry_save_path.grid(row=2, column=1, padx=10, pady=5)
    tk.Button(edit_window, text="Choisir", command=lambda: select_directory(entry_save_path)).grid(row=2, column=2, padx=10, pady=5)

    # Chemin de l'image
    tk.Label(edit_window, text="Chemin de l'image :").grid(row=3, column=0, padx=10, pady=5, sticky="w")
    entry_image_path = tk.Entry(edit_window, width=40)
    entry_image_path.insert(0, game['image_path'])
    entry_image_path.grid(row=3, column=1, padx=10, pady=5)
    tk.Button(edit_window, text="Choisir", command=lambda: select_file(entry_image_path, [("Images", "*.jpg;*.jpeg;*.png")])).grid(row=3, column=2, padx=10, pady=5)

    # Sauvegarde des changements
    def save_changes(game, config_path, root, edit_window):
        updated_data = {
            'name': entry_name.get(),
            'exe_path': entry_exec_path.get(),
            'save_path': entry_save_path.get(),
            'image_path': entry_image_path.get()
        }

        update_game_info(game, config_path, updated_data)
        edit_window.destroy()  # Fermer la fenêtre d'édition
        root.destroy()  # Fermer la fenêtre principale
        config = load_config(config_path)  # Recharger la configuration mise à jour
        create_ui(config, config_path)  # Relancer l'interface avec la nouvelle configuration

    # Bouton pour enregistrer les modifications
    tk.Button(edit_window, text="Enregistrer", command=lambda: save_changes(game, config_path, root, edit_window)).grid(row=4, column=1, padx=10, pady=10)

def create_ui(config, config_path):
    """
    Crée l'interface utilisateur principale.
    """
    root = tk.Tk()
    root.title("Gestionnaire de Sauvegardes")
    root.configure(bg="black")
    root.geometry("800x600")

    # Bouton Paramètres FTP en haut à gauche
    btn_ftp = tk.Button(
        root,
        text="Paramètres FTP",
        command=lambda: edit_ftp_config_info(config_path, root)
    )
    btn_ftp.grid(row=0, column=0, sticky="nw", padx=10, pady=10)

    games = config['games']
    server_config = config['server']

    # Définir les colonnes (4 jeux par ligne)
    columns = 4

    for index, game in enumerate(games):
        row = index // columns
        col = index % columns

        # Conteneur pour chaque jeu
        frame = tk.Frame(root, bg="black", padx=10, pady=10)
        frame.grid(row=row+1, column=col, sticky="n")

        # Charger l'image et la redimensionner
        img = Image.open(game['image_path'])
        img = img.resize((150, 150), Image.LANCZOS)
        img = ImageTk.PhotoImage(img)

        # Image du jeu
        label_img = tk.Label(frame, image=img, bg="black")
        label_img.image = img
        label_img.pack()

        # Nom du jeu
        label_name = tk.Label(frame, text=game['name'], font=("Arial", 14), fg="white", bg="black")
        label_name.pack()

        # Boutons d'action
        btn_download = tk.Button(
            frame,
            text="Download",
            command=lambda g=game: download_save(g, server_config)
        )
        btn_download.pack(fill="x", pady=2)

        btn_upload = tk.Button(
            frame,
            text="Upload",
            command=lambda g=game: upload_save(g, server_config)
        )
        btn_upload.pack(fill="x", pady=2)

        btn_launch = tk.Button(
            frame,
            text="Start game",
            command=lambda g=game: launch_game(g)
        )
        btn_launch.pack(fill="x", pady=2)

        # Bouton pour modifier les informations
        btn_edit = tk.Button(
            frame,
            text="Modifier",
            command=lambda g=game: edit_game_info(g, config_path, root)
        )
        btn_edit.pack(fill="x", pady=2)

    root.mainloop()


if __name__ == "__main__":
    config = load_config()
    create_ui(config,config_path='games.yml')
