// const api_url = "https://bostadspriser-api.app.cloud.cbh.kth.se";
const api_url = "http://localhost:8080";

export const getListings = async (n, skip) => {
  if (n === undefined) {
    n = 10;
  }
  if (skip === undefined) {
    skip = 0;
  }
  const response = await fetch(api_url + "/listings?n=" + n + "&skip=" + skip);
  const data = await response.json();

  return data;
};

export const getLocations = async () => {
  const response = await fetch(api_url + "/locations");
  const data = await response.json();

  return data;
}


export const predict = async (listing) => {
  const response = await fetch(api_url + "/predict", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(listing),
  });

  if (response.status !== 200) {
    return response.json();
  }

  return response.json();
};