from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from googleapiclient.http import MediaIoBaseDownload
from tqdm import tqdm

# Step 1: Authenticate
gauth = GoogleAuth()
gauth.LoadCredentialsFile("mycreds.txt")  # Load credentials from a file if available
if gauth.credentials is None:
    # Authenticate if they're not there
    gauth.LocalWebserverAuth()
elif gauth.access_token_expired:
    # Refresh them if expired
    gauth.Refresh()
else:
    # Initialize the saved creds
    gauth.Authorize()
gauth.SaveCredentialsFile("mycreds.txt")  # Save the current credentials to a file

# Step 2: Create GoogleDrive instance with authenticated GoogleAuth instance
drive = GoogleDrive(gauth)

def list_files_and_folders(parent_id='root'):
    not_own_query = f"'{parent_id}' in parents and trashed=false and not 'me' in owners"
    own_query = f"'{parent_id}' in parents and trashed=false and 'me' in owners"
    not_own_file_list = drive.ListFile({'q': not_own_query}).GetList()
    own_file_list = drive.ListFile({'q': own_query}).GetList()

    file_list = not_own_file_list + own_file_list
    print("Files and folders in the current directory:")
    for i, file in enumerate(file_list):
        ownership = " (Not Owned)" if file in not_own_file_list else ""
        print(f"{i + 1}. {file['title']} - {'Folder' if file['mimeType'] == 'application/vnd.google-apps.folder' else 'File'}{ownership}")
    return file_list

def download_file_with_progress(file):
    file_size = int(file['fileSize'])
    with open(file['title'], 'wb') as f:
        request = drive.auth.service.files().get_media(fileId=file['id'])
        downloader = MediaIoBaseDownload(f, request)
        done = False
        with tqdm(total=file_size, unit='B', unit_scale=True, desc=file['title']) as pbar:
            while done is False:
                status, done = downloader.next_chunk()
                pbar.update(status.resumable_progress - pbar.n)

    # Delete the file from Google Drive after download
    file.Delete()
    print(f"File '{file['title']}' deleted from Google Drive.")

    # Reupload the file to the same Google Drive directory
    new_file = drive.CreateFile({'title': file['title'], 'parents': [{'id': file['parents'][0]['id']}]})
    new_file.SetContentFile(file['title'])
    new_file.Upload()
    print(f"File '{file['title']}' reuploaded to Google Drive.")

def main():
    current_folder_id = 'root'
    while True:
        file_list = list_files_and_folders(current_folder_id)
        file_index = int(input("Enter the number of the file/folder you want to select (0 to go back): ")) - 1
        if file_index == -1:
            if current_folder_id == 'root':
                print("You are already in the root directory.")
            else:
                current_folder_id = 'root'  # For simplicity, going back to root
        else:
            selected_file = file_list[file_index]
            if selected_file['mimeType'] == 'application/vnd.google-apps.folder':
                current_folder_id = selected_file['id']
            else:
                download_file_with_progress(selected_file)
                print(f"File '{selected_file['title']}' downloaded successfully!")
                break

if __name__ == "__main__":
    main()