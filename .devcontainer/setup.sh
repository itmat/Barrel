CREDENTIALS_DIRECTORY=$PWD/.devcontainer/credentials

mkdir -p $CREDENTIALS_DIRECTORY

SSH_DIRECTORY=$CREDENTIALS_DIRECTORY/.ssh
AWS_DIRECTORY=$CREDENTIALS_DIRECTORY/.aws

rm -rf ~/.ssh
ln -s $SSH_DIRECTORY ~/.ssh
ln -s $AWS_DIRECTORY ~/.aws

if [ ! -d $SSH_DIRECTORY ]; then
    mkdir -m 700 $SSH_DIRECTORY
fi

if [ ! -d $AWS_DIRECTORY ]; then
    read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
    read -p "AWS Secret Access Key (input will not be echoed): " -s AWS_SECRET_ACCESS_KEY; echo
    read -p "Default region name: " DEFAULT_REGION_NAME

    mkdir -m 700 $AWS_DIRECTORY

    echo "[default]"                                        >  $AWS_DIRECTORY/credentials
    echo "aws_access_key_id=$AWS_ACCESS_KEY_ID"             >> $AWS_DIRECTORY/credentials
    echo "aws_secret_access_key=$AWS_SECRET_ACCESS_KEY"     >> $AWS_DIRECTORY/credentials

    echo "[default]"                                        >  $AWS_DIRECTORY/config
    echo "region=$DEFAULT_REGION_NAME"                      >> $AWS_DIRECTORY/config
    echo "output=json"                                      >> $AWS_DIRECTORY/config
fi

npm install

sudo pip install --requirement requirements-dev.txt
sudo pip install --requirement requirements.txt
sudo pip install --editable barrel/worker

echo 'export PATH=$PATH:'$PWD'/node_modules/aws-cdk/bin' >> ~/.bashrc
echo 'export PYTHONDONTWRITEBYTECODE=1' >> ~/.bashrc

ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts
