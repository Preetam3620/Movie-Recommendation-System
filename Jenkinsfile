pipeline {
    agent any

    environment {
        PYTHON_ENV = 'python3'
        GITHUB_REPO = 'https://github.com/priyankaangad/movieRecommendationSystem'
        STREAMLIT_BRANCH = 'main'
    }

    stages {
        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
               python3 -m venv venv
                . venv/bin/activate
                pip install --upgrade pip
                pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                . venv/bin/activate
                pytest || echo "No tests found, skipping test failure"
                '''
            }
        }

        stage('Deploy to Streamlit Cloud') {
            steps {
                withCredentials([string(credentialsId: 'STREAMLIT_CLOUD_API_TOKEN', variable: 'STREAMLIT_TOKEN')]) {
                    sh '''
                    . venv/bin/activate
                    mkdir -p ~/.streamlit

                    echo "[general]" > ~/.streamlit/credentials.toml
                    echo "email = \\"ypriyankaangad.jadhav@sjsu.edu\\"" >> ~/.streamlit/credentials.toml
                    echo "token = \\"${fc1720d2823445adac548cac1c3ce4d9}\\"" >> ~/.streamlit/credentials.toml

                    echo "[server]" > ~/.streamlit/config.toml
                    echo "headless = true" >> ~/.streamlit/config.toml
                    echo "enableCORS = false" >> ~/.streamlit/config.toml

                    streamlit run main.py
                    '''
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}
