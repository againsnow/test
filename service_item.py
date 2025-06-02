class RepositoryHash:

    @staticmethod
    def add_item_hash_in_file(account_name: str, item_hash: str):
        with open(f"databases/{account_name}", "a") as file:
            file.write(f'{item_hash}\n')
    @staticmethod
    def remove_item_hash_from_txt(account_name: str, item_hash: str):
        with open(f'databases/{account_name}', 'r') as f:
            lines = f.readlines()
        lines = [line for line in lines if line.strip() != item_hash]
        with open(f'databases/{account_name}', 'w') as f:
            f.writelines(lines)

    @staticmethod
    def is_item_in_txt(account_name: str, item_hash: str):
        with open(f'databases/{account_name}', 'r') as f:
            for line in f:
                if line.strip() == str(item_hash):
                    return True
        return False
