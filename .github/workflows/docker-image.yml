name: Build and Push Docker Image to ECR

on:
  push:
    branches: ["main"]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:

      - name: Checkout Code
        uses: actions/checkout@v4.2.2

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-south-1

      - name: Login to Amazon ECR
        run: |
          aws ecr get-login-password --region ap-south-1 | \
          docker login --username AWS --password-stdin 203918855762.dkr.ecr.ap-south-1.amazonaws.com

      - name: Build Docker Image
        run: |
          docker build -t dk .

      - name: Tag Docker Image
        run: |
          docker tag dk:latest 203918855762.dkr.ecr.ap-south-1.amazonaws.com/dk:latest

      - name: Push Docker Image
        run: |
          docker push 203918855762.dkr.ecr.ap-south-1.amazonaws.com/dk:latest
