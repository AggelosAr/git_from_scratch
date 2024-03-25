import sys
import os
import zlib
import hashlib
from typing import Tuple
# TOTO clone
def main():

    command = sys.argv[1]
    if command == "init":
        git_init()
    elif command == "cat-file":
        if sys.argv[2] != "-p":
            raise RuntimeError(f"Unknown command #{sys.argv[2]}")
        res = git_cat_blob(sha1=sys.argv[3])
        print(res, end="")
    elif command == "hash-object":
        if sys.argv[2] != "-w":
            raise RuntimeError(f"Unknown command #{sys.argv[2]}")
        blob, sha1, _ = create_new_blob(path_to_file=sys.argv[3])
        store_new_data(blob, sha1[:2], sha1[2:])
        print(sha1, end="")
    elif command == "write-tree":
        sha1, _ = write_tree(path= os.getcwd())
        print(sha1, end="")
    elif command == "ls-tree":
       
        res = git_ls_tree(sha1=sys.argv[3])
        res = res.split('\n')
        if 'tree' not in res[0]:
            raise RuntimeError(f"Blob is not a tree")
        
       
        if sys.argv[2] == "--name-only":
            for el in res[1:]:
                print(el.split(" ")[-1])
        elif sys.argv[2] == "--ALL":
            for el in res:
                print(el)
        else:
            raise RuntimeError(f"Unknown command #{sys.argv[2]}")
    

    # this is hardcoded/
    # 1st arg should be the tree sha 
    # then -p with parent sha 
    # then -m with message
    elif command == "commit-tree":
        parent_sha = ""
        author_name = "Aggelos"
        email = "test@test.com"
        #ts = 1
        tree_sha = sys.argv[2]
        parent_sha = sys.argv[4]
        message = sys.argv[6]

        sha = create_new_commit(tree_sha, parent_sha, author_name, email, message )
        print(sha)
    elif command == "print-commit":
       print_commit(sys.argv[2])

    else:
        raise RuntimeError(f"Unknown command #{command}")



def git_init():
    os.mkdir(".git")
    os.mkdir(".git/objects")
    os.mkdir(".git/refs")
    with open(".git/HEAD", "w") as f:
        f.write("ref: refs/heads/main\n")
    print("Initialized git directory")


def git_cat_blob(sha1: str) -> str:
    blob_dir, blob_file_name = sha1[:2], sha1[2:]
    with open(f".git/objects/{blob_dir}/{blob_file_name}", "rb") as data:
        decompressed_blob = bytes_decompress(data.read())
    return bytes_to_string(b''.join(decompressed_blob.split(b'\x00')[1:]))

def git_ls_tree(sha1: str) -> str:
    tree_dir, tree_file_name = sha1[:2], sha1[2:]
    with open(f".git/objects/{tree_dir}/{tree_file_name}", "rb") as data:
        decompressed_blob = bytes_decompress(data.read())
    return bytes_to_string(b''.join(decompressed_blob.split(b'\x00')))

def create_new_blob(path_to_file: str) -> Tuple[bytes, str, int]:
    with open(f"{path_to_file}") as f:
        data = f.read()
    
    bytes_data, sha1, _, _ = get_data_info(data)
    blob, size = compress_blob(bytes_data)
    return blob, sha1, size


def create_new_tree(data: str, size: int) -> Tuple[bytes, str, int]:
    bytes_data, sha1, _, _ = get_data_info(data)
    tree = compress_tree(bytes_data, size)
    return tree, sha1


def get_tree_size(sha: str) -> str:
    return git_ls_tree(sha).split('\n')[0].split(" ")[1]

def create_new_commit(tree_sha, parent_sha, author_name, email, message) -> Tuple[str, bytes]:
    
    headers = f"commit {get_tree_size(tree_sha)}\0\n"
    headers += f"author {author_name} <{email}>\0\n"
    headers += f"parent {parent_sha}\0\n"
    headers += f"tree {tree_sha}\0\n"
    
    headers += f"{message}\0\n"

    compressed_data = compress_bytes(string_to_bytes(headers))
    sha = get_sha_of_str(headers)
    store_new_data(compressed_data, sha[:2], sha[2:])
    return sha

def print_commit(sha: str):
    commit_dir, commit_file_name = sha[:2], sha[2:]
    with open(f".git/objects/{commit_dir}/{commit_file_name}", "rb") as data:
        decompressed_blob = bytes_decompress(data.read())
    for el in bytes_to_string(b''.join(decompressed_blob.split(b'\x00'))).split('\n'):
        print(el)
    

def store_new_data(data: bytes, 
                   dir_name: str, 
                   file_name: str):
    os.mkdir(f".git/objects/{dir_name}")
    with open(f".git/objects/{dir_name}/{file_name}", "wb") as f:
        f.write(data)


    
# Create some random files and directories:
# Then use write_tree
def write_tree(path: str) -> Tuple[str, int]:
    is_tree = False
    curr_entries = []
    total_size = 0

    for el in os.listdir(path):
        if el in ['.git', 'main.py']:
            continue
        
        new_path = os.path.join(path, el)
        size = 0
        mode, name, sha1  = "", "", ""
        
        # 100755 (executable file), 120000 (symbolic link)
        if os.path.isdir(el):
            mode, name = "040000", "tree"
            sha1, size = write_tree(path=new_path)
            
        else:
           is_tree = True
           mode, name = "100644", "blob"
           blob, sha1, size = create_new_blob(path_to_file=new_path)
           store_new_data(blob, sha1[:2], sha1[2:])
          

        curr_entries.append(f"{mode} {name}\0{sha1} {el}")
        total_size += size
    
    sha1 = ""
    if is_tree:
        # /n to make our life easier
        tree, sha1 = create_new_tree('\n'.join(curr_entries), total_size)
        store_new_data(tree, sha1[:2], sha1[2:])
      
    #for el in curr_entries:
    #    print(el, " -> DEBUG")

    return sha1, total_size


def compress_blob(bytes_data) -> Tuple[bytes, int]:
    compressed_content = compress_bytes(bytes_data)
    headers = f"blob {len(compressed_content)}\0"
    return compress_bytes(string_to_bytes(headers) + bytes_data), len(compressed_content)

def compress_tree(bytes_data, size) -> Tuple[bytes, int]:
    headers = f"tree {size}\0\n"
    return compress_bytes(string_to_bytes(headers) + bytes_data)


def get_sha_of_str(data: str):
    bytes_data = string_to_bytes(data)
    full_name = hashlib.sha1(bytes_data)
    sha1 = full_name.hexdigest()
    return sha1

def get_data_info(data: str):
    bytes_data = string_to_bytes(data)
    full_name = hashlib.sha1(bytes_data)
    sha1 = full_name.hexdigest()
    dir_name = sha1[:2]
    file_name = sha1[2:]
    return bytes_data, sha1, dir_name, file_name

def string_to_bytes(data: str) -> bytes:
    return str.encode(data)

def compress_bytes(data: bytes) -> bytes:
    return zlib.compress(data)

def bytes_decompress(data: bytes) -> bytes:
    return zlib.decompress(data)

def bytes_to_string(data: bytes) -> str:
    return data.decode()


if __name__ == "__main__":
    """
    try:
        store_blob()
    except:
        pass
    """
    main()


# On trees we append /n for easy :0

# python main.py init
# Create random folders and txts
# python main.py write-tree ( get the sha from the output)
# python main.py ls-tree --ALL SHA

# python main.py commit-tree TREE_SHA -p PARENT_SHA(not used for now) -m "WOW COMMIT" -> prints the sha of the commit
# python main.py print-commit COMMIT_SHA


# Create a test.txt
# python main.py hash-object -w test.txt -> get the sha
# Add the hash to cat-file
# python main.py cat-file -p sha
    
    